import os
import boto3
import glob
import json
import shutil
from natsort import natsorted
from urllib.parse import unquote_plus, urlparse
from datetime import datetime
import random
import moviepy.config as mpy_config

# MoviePy imports for clip duration and component composition
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    ColorClip,
)

# --- GLOBAL CONFIGURATION (Safe and Stable) ---

# Initialize the S3 client globally
s3_client = boto3.client("s3")
# Initialize Lambda's temporary directory globally
tmp_dir = "/tmp"

# Define the fallback image directory
FALLBACK_IMAGE_DIR = "/var/task/images"

# Define the archive prefix globally
ARCHIVE_PREFIX = "processed-input/"

# Target video resolution defaults
DEFAULT_ASPECT_RATIO = "16:9"

# --- STABLE TRANSITION PATH RESTORED ---
TRANSITION_VIDEO_PATH = "/var/task/fade_transition.mp4"

# --- CONFIGURATION FOR TITLE SLIDE ---
TITLE_FONT_SIZE = 110
TITLE_STROKE_WIDTH = 5
# Safe character limit for the large title font to force wrapping
MAX_CHARS_PER_TITLE_LINE = 8
# ------------------------------------

# --- OPTIMIZATION 1: FFmpeg Binary Setup (Runs once on Cold Start) ---
try:
    ffmpeg_source = "/var/task/ffmpeg"
    ffmpeg_dest = os.path.join(tmp_dir, "ffmpeg")
    # Only copy if the file doesn't exist (i.e., on cold start)
    if not os.path.exists(ffmpeg_dest):
        shutil.copy(ffmpeg_source, ffmpeg_dest)
        os.chmod(ffmpeg_dest, 0o755)  # Ensure it's executable
        print("FFmpeg copied and set up on disk (Cold Start).")
    else:
        print("FFmpeg already present in /tmp. Skipping copy (Warm Start).")
except Exception as e:
    print(f"FATAL: Failed to copy or set permissions for FFmpeg: {e}")
    # Fatal error at module load time will crash the Lambda before invocation
    raise

# Explicitly set ffmpeg path (relies on copy above)
mpy_config.FFMPEG_BINARY = os.path.join(tmp_dir, "ffmpeg")

# --- UTILITY FUNCTION: S3 Object Move (Unchanged) ---


def move_s3_object(bucket, old_key, new_key):
    """
    Moves a single S3 object from old_key to new_key within the same bucket
    via copy and delete operations.
    """
    print(f"Archiving object from {old_key} to {new_key}")
    try:
        # 1. Copy the object
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": old_key},
            Key=new_key,
        )

        # 2. Delete the original object
        s3_client.delete_object(Bucket=bucket, Key=old_key)
        print(f"Successfully archived {old_key}")
    except Exception as e:
        print(f"WARNING: Failed to archive object {old_key}. Error: {e}")


# --- CORE FUNCTION: COMBINE VIDEOS (Unchanged) ---


def combine_videos(video_paths: list, final_output_path: str):
    """
    Combines a list of video files into a single final video.
    Includes explicit resource handling to prevent FFMPEG read errors.
    """
    print(f"Combining {len(video_paths)} videos into {final_output_path}...")

    if not video_paths:
        print("No videos to combine. Skipping final step.")
        return

    # --- RE-INJECT ENVIRONMENT OVERRIDES ---
    os.environ["TMPDIR"] = tmp_dir
    os.environ["TEMP"] = tmp_dir
    os.environ["TMP"] = tmp_dir
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    # ----------------------------------------------------

    clips = []
    final_clip = None
    try:
        # Load all clips from the list of paths with error handling
        for path in video_paths:
            try:
                # Attempt to load the intermediate clip
                clip = VideoFileClip(path)
                clips.append(clip)
            except Exception as e:
                # Log a warning for a failed intermediate clip, but continue
                print(
                    f"CRITICAL WARNING: Failed to read intermediate video {path}: {e}"
                )
                continue

        if not clips:
            print(
                "No clips successfully loaded after attempt to read intermediate files. Skipping combination."
            )
            return

        # Concatenate the clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the final combined video file
        final_clip.write_videofile(
            final_output_path, codec="libx264", audio_codec="aac"
        )
        print(f"Final video successfully combined at {final_output_path}")

    except Exception as e:
        print(f"An error occurred during video combination: {e}")
        raise

    finally:
        # Restore the original working directory
        os.chdir(original_cwd)
        # Explicitly close all clips to free up resources (CRITICAL for MoviePy stability)
        if clips:
            for clip in clips:
                clip.close()
        if final_clip:
            final_clip.close()


# --- UTILITY FUNCTION: DYNAMIC SUBTITLE GENERATOR (Unchanged) ---


def generate_timed_text_clips(
    text: str, duration: float, font_path: str, max_words_per_chunk: int
):
    """
    Splits text into chunks, prioritizing sentence structure/punctuation breaks,
    while respecting a maximum word count per chunk.
    """
    words = text.split()
    chunks = []
    current_chunk = []

    # Define punctuation marks that signal a good pause point for a subtitle break
    PAUSE_PUNCTUATION = [".", ",", ":", ";", "!", "?"]

    # 1. Chunk the text based on punctuation or max word count
    for word in words:
        current_chunk.append(word)

        # Check if the chunk is at the maximum size OR if the last word ends with a pause punctuation
        is_max_size = len(current_chunk) >= max_words_per_chunk
        is_pause_point = (
            word.strip()[-1] in PAUSE_PUNCTUATION if len(word) > 0 else False
        )

        if is_max_size or is_pause_point:
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    # Add any remaining words
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    if not chunks:
        return []

    # 2. Calculate even duration per chunk
    time_per_chunk = duration / len(chunks)

    timed_clips = []
    current_time = 0.0

    # 3. Create time-coded clips (API Fixes: text, font_size)
    for chunk in chunks:
        clip = (
            TextClip(
                text=chunk,
                font=font_path,
                font_size=40,
                color="white",
                stroke_color="black",
                stroke_width=2,
            )
            .with_duration(time_per_chunk)
            .with_start(current_time)
            .with_position("center")
        )
        timed_clips.append(clip)
        current_time += time_per_chunk

    return timed_clips


# --- NEW UTILITY FUNCTION: TITLE GENERATOR (FIXED: Dynamic Wrapping) ---


def generate_title_clip(text: str, duration: float, font_path: str):
    """
    Generates a single, large, bold, centered text clip for a title card.
    Applies dynamic wrapping based on MAX_CHARS_PER_TITLE_LINE to prevent text overflow.
    """

    # 1. Implement simple wrapping logic based on character count
    words = text.split()
    wrapped_lines = []
    current_line = []

    for word in words:
        # Check if adding the word exceeds the limit and the current line is NOT empty
        current_char_count = sum(len(w) + 1 for w in current_line)
        if current_char_count + len(word) > MAX_CHARS_PER_TITLE_LINE and current_line:
            wrapped_lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)

    if current_line:
        wrapped_lines.append(" ".join(current_line))

    wrapped_text = "\n".join(wrapped_lines)
    print(f"Wrapped Title Text:\n{wrapped_text}")

    # 2. Create the TextClip with the wrapped text
    title_clip = (
        TextClip(
            text=wrapped_text,  # Use the wrapped text
            font=font_path,
            font_size=TITLE_FONT_SIZE,
            color="white",
            stroke_color="black",
            stroke_width=TITLE_STROKE_WIDTH,
        )
        .with_duration(duration)
        .with_start(0.0)
        .with_position("center")
    )
    return [title_clip]


# --- UTILITY FUNCTION: IMAGE RESIZE AND CROP (FIXED: Switched to FIT/Padded Mode) ---


def resize_and_crop_image(
    image_path: str, target_width: int, target_height: int, output_path: str = None
) -> str:
    """
    FIXED: Resizes the image to FIT (Letterbox/Pillarbox) within the target resolution
    to preserve all content (no cropping). The final output file is the exact target size.
    """
    original_clip = None
    final_output_path = output_path if output_path else image_path

    # Ensure output is PNG for quality and to avoid issues with saving composite frames
    if not final_output_path.lower().endswith(".png"):
        final_output_path = final_output_path.rsplit(".", 1)[0] + ".png"

    try:
        original_clip = ImageClip(image_path)
        width, height = original_clip.size

        print(
            f"Processing image: {os.path.basename(image_path)}. Original size: {width}x{height}. Target: {target_width}x{target_height}. MODE: FIT/PAD."
        )

        # 1. Calculate the scaling factor to FIT the image entirely within the target frame
        scale_factor = min(target_width / width, target_height / height)

        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # 2. Resize the image clip only
        resized_clip = original_clip.resized(width=new_width, height=new_height)

        # 3. Create a black background clip (the canvas) at the final target size
        # Must give it a non-zero duration to make it composable
        background_clip = ColorClip(
            size=(target_width, target_height),
            color=[0, 0, 0],  # Solid black for padding
            duration=0.01,
        )

        # 4. Calculate offsets for centering
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2

        # 5. Composite the resized image onto the center of the black background
        # We ensure the duration matches for the save_frame method below
        final_clip_composite = CompositeVideoClip(
            [
                background_clip,
                resized_clip.with_position((x_offset, y_offset)).with_duration(0.01),
            ],
            size=(target_width, target_height),
        )

        # 6. Save the frame of the composite clip as the final image file
        final_clip_composite.save_frame(
            final_output_path, t=0
        )  # t=0 ensures we grab the first frame

        print(
            f"Successfully padded and saved (Fit mode) to {final_output_path} (Padded image size: {new_width}x{new_height})"
        )
        return final_output_path

    except Exception as e:
        print(f"FATAL WARNING: Image processing failed for {image_path}. Error: {e}")
        # Log the failure but return the original path so the video creation *might* still proceed with an un-processed image.
        return image_path

    finally:
        # Explicitly close all clips to free up memory (CRITICAL)
        if original_clip:
            original_clip.close()
        try:
            if "background_clip" in locals():
                background_clip.close()
            if "resized_clip" in locals():
                resized_clip.close()
            if "final_clip_composite" in locals():
                final_clip_composite.close()
        except Exception:
            pass


# --- CORE FUNCTION: CREATE VIDEO (Updated) ---


def create_video_from_images_and_audio(
    image_folder: str,
    audio_path: str,
    output_path: str,
    segment_text: str,
    is_header_segment: bool = False,
    word_chunk_size: int = 4,
    target_width: int = 1920,
    target_height: int = 1080,
    fps: int = 1,
):
    """
    Creates a video from a sequence of images and a single audio file from local paths.
    """
    if not os.path.isfile(audio_path):
        print(f"Error: The specified audio file '{audio_path}' does not exist.")
        return False

    # --- DURATION CALCULATION (Simplified) ---
    try:
        audio_clip_temp = AudioFileClip(audio_path)
        audio_duration = audio_clip_temp.duration
        audio_clip_temp.close()
    except Exception as e:
        print(f"FATAL: Could not load audio to determine duration: {e}")
        return False

    MIN_ENCODE_DURATION = 1.0
    video_segment_duration = max(audio_duration, MIN_ENCODE_DURATION)
    # --- END DURATION CALCULATION ---

    # --- IMAGE SELECTION AND PROCESSING LOGIC (Uses new dynamic targets) ---
    local_image_files = [
        os.path.join(image_folder, img)
        for img in os.listdir(image_folder)
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    image_files = natsorted(local_image_files)
    image_source = image_folder

    initial_image_paths = []

    # DETERMINE INITIAL IMAGE LIST (Downloaded or Fallback)
    if not image_files:
        fallback_images = glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.png"))
        fallback_images.extend(glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.jpg")))

        fallback_images.extend(glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.jpeg")))

        if fallback_images:
            random_image_path = random.choice(fallback_images)
            initial_image_paths = [random_image_path]
            image_source = f"RANDOM image: {os.path.basename(random_image_path)}"
            print(
                f"Warning: No segment images found. Falling back to a SINGLE, {image_source}."
            )
        else:
            print(
                f"Error: No images found and no sample images found in '{FALLBACK_IMAGE_DIR}'. Skipping segment."
            )
            return False
    else:
        initial_image_paths = image_files

    # PROCESS AND RESIZE IMAGES (Copy and Overwrite)
    final_image_paths = []
    temp_copies_to_cleanup = []

    for path in initial_image_paths:
        current_path = path

        if not path.startswith(tmp_dir):
            base_name = os.path.basename(path).rsplit(".", 1)[0]
            temp_path = os.path.join(image_folder, f"{base_name}_temp_copy.png")
            shutil.copy(path, temp_path)
            current_path = temp_path
            temp_copies_to_cleanup.append(temp_path)

        resized_path = resize_and_crop_image(
            current_path, target_width, target_height, output_path=current_path
        )
        final_image_paths.append(resized_path)

    image_files = final_image_paths
    # --- END IMAGE SELECTION AND PROCESSING LOGIC ---

    print(
        f"Content duration: {video_segment_duration:.2f}s. Target Res: {target_width}x{target_height}."
    )

    # --- CWD OVERRIDE FOR SUBPROCESS SAFETY ---
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    # ----------------------------------------

    audio_clip = None
    video_clip = None
    clips = []
    subtitle_clips = []
    video_clip_edit = None

    try:
        # 1. Load the audio clip
        audio_clip = AudioFileClip(audio_path)

        # 2. Calculate the duration for each image
        num_images = len(image_files)
        image_duration = video_segment_duration / num_images
        print(f"Each image will be shown for {image_duration:.2f} seconds.")

        # 3. Create and concatenate image clips.
        clips = [ImageClip(path, duration=image_duration) for path in image_files]

        video_clip = concatenate_videoclips(clips, method="compose")
        video_clip.duration = video_segment_duration
        video_clip.audio = audio_clip  # Audio starts immediately

        # --- DYNAMIC SUBTITLE LOGIC ---
        font_file = "/var/task/fonts/SubtitleFont.ttf"
        positioned_subtitle_clips = []

        if is_header_segment:
            # Use the specialized title generator for header slides
            print("Generating Header/Title Clip (Large, Centered)...")
            subtitle_clips = generate_title_clip(
                segment_text, video_segment_duration, font_file
            )
            # Title clips are already centered, no need to reposition
            positioned_subtitle_clips = subtitle_clips

        else:
            # Use the standard, chunked subtitle generator for content slides
            print(
                f"Generating Standard Subtitle Clips (Chunked: {word_chunk_size}, Bottom-Aligned)..."
            )
            subtitle_clips = generate_timed_text_clips(
                segment_text,
                video_segment_duration,
                font_file,
                max_words_per_chunk=word_chunk_size,  # DYNAMIC CHUNK SIZE
            )

            for clip in subtitle_clips:
                # Reposition standard subtitles to the bottom (relative to the dynamic height)
                clip = clip.with_position(("center", target_height * 0.9))
                positioned_subtitle_clips.append(clip)

        # --- END DYNAMIC SUBTITLE LOGIC ---

        # 4. BUILD THE FINAL COMPOSITE CLIP
        video_clip_edit = CompositeVideoClip(
            [video_clip] + positioned_subtitle_clips, size=(target_width, target_height)
        )
        video_clip_edit.duration = video_segment_duration
        video_clip_edit.audio = video_clip.audio

        # Step 5: Write the video file.
        video_clip_edit.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            # Enforce uniform video properties for stable concatenation
            ffmpeg_params=[
                "-vf",
                f"scale={target_width}:{target_height}",
                "-pix_fmt",
                "yuv420p",
            ],
        )
        print(f"Video successfully created at {output_path}")
        return True

    except Exception as e:
        print(f"An error occurred during video creation: {e}")
        raise

    finally:
        os.chdir(original_cwd)
        # Cleanup clips (Explicitly close all clips)
        if audio_clip:
            audio_clip.close()
        if video_clip:
            video_clip.close()
        if video_clip_edit:
            video_clip_edit.close()
        if clips:
            for clip in clips:
                clip.close()
        if subtitle_clips:
            for clip in subtitle_clips:
                clip.close()

        # CLEANUP: Delete the temporary copies made from the read-only FALLBACK_IMAGE_DIR
        for path in temp_copies_to_cleanup:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Warning: Failed to cleanup temp image file {path}: {e}")


# --- FINAL LAMBDA HANDLER (UPDATED with Config extraction and Final Cleanup) ---


def lambda_handler(event, context):
    print("Received event:", event)

    # Store a variable for the compilation ID, initialized to a fallback value
    compilation_id = datetime.now().strftime("%Y%m%d%H%M%S")

    # Initialize config variables with defaults
    word_chunk_size = 4
    transition_style = "fade"
    target_width = 1920
    target_height = 1080

    # Define local path for the JSON manifest (used in cleanup)
    local_json_path = ""
    # Define local path for the final output file (used in cleanup)
    final_output_file = ""

    try:
        # 1. Determine Bucket and Key (Assuming S3 trigger on highlights.json)
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        # The JSON manifest key must be URL-decoded because S3 event keys are encoded
        json_key = unquote_plus(record["s3"]["object"]["key"], encoding="utf-8")

        print(f"Processing JSON manifest from s3://{bucket}/{json_key}")

        # 2. Download and Parse highlights.json
        local_json_path = os.path.join(tmp_dir, os.path.basename(json_key))
        s3_client.download_file(bucket, json_key, local_json_path)

        with open(local_json_path, "r") as f:
            full_manifest = json.load(f)

        # --- EXTRACT ID AND CONFIGURATION ---
        compilation_id = full_manifest.get("id", compilation_id)
        highlights_data = full_manifest.get("highlights", [])

        # --- NEW: EXTRACT CONFIGURATION PARAMETERS ---
        config = full_manifest.get("config", {})

        # A. Aspect Ratio (Updates TARGET_WIDTH/HEIGHT)
        ratio_str = config.get("ratio", DEFAULT_ASPECT_RATIO)

        if ratio_str == "9:16":
            target_width, target_height = 1080, 1920  # Vertical (Shorts/Mobile)
        elif ratio_str == "1:1":
            target_width, target_height = 1080, 1080  # Square (Social)
        else:  # Defaults to 16:9
            target_width, target_height = 1920, 1080

        print(
            f"Set video resolution to {target_width}x{target_height} based on ratio: {ratio_str}"
        )

        # B. Transition Style
        transition_style = config.get("transition", "fade")  # Supports 'fade' and 'cut'
        print(f"Set transition style to: {transition_style}")

        # C. Word Chunk Size
        word_chunk_size = config.get("word_chunk", 4)
        # Ensure it's an integer, fallback to 4 if invalid
        try:
            word_chunk_size = int(word_chunk_size)
        except ValueError:
            word_chunk_size = 4

        print(f"Set word chunk size to: {word_chunk_size}")
        # ------------------------------------------

        # 3. Sort the data by 'order' field
        highlights_data.sort(key=lambda x: x.get("order", 9999))
        print(f"Found {len(highlights_data)} segments. Sorted by 'order'.")

        intermediate_video_paths = []
        successful_audio_keys = []  # List to track S3 keys to archive

        # 4. Loop through each ordered segment to create intermediate videos
        for i, segment in enumerate(highlights_data):
            order = segment.get("order", i)
            audio_s3_key = segment.get("audio")

            # --- HEADER LOGIC CHECK ---
            is_header_segment = order == 0
            print(f"Is Header Segment: {is_header_segment}")
            # --------------------------

            # Extract the segment text, using a fallback if missing
            segment_text = segment.get("text", "No Text Provided")

            segment_name = f"segment_{order:03d}"

            print(
                f"\n--- Starting processing for segment: {segment_name} (Order {order}) ---"
            )
            print(f"Segment Text: '{segment_text}'")

            if not audio_s3_key:
                print(f"Skipping segment {order}: 'audio' key missing.")
                continue

            # --- PREPARE LOCAL FOLDERS & PATHS ---
            local_subfolder = os.path.join(tmp_dir, segment_name)
            os.makedirs(local_subfolder, exist_ok=True)

            # --- S3 IMAGE DOWNLOAD (FIX APPLIED: Extracting key from full URL) ---
            if image_data := segment.get("image", {}):
                image_s3_key_url = image_data.get("s3_key")

                if image_s3_key_url:
                    s3_key_raw = image_s3_key_url

                    # 1. Extract the key/path if it's a full URL
                    if s3_key_raw.startswith("http"):
                        parsed_url = urlparse(s3_key_raw)
                        s3_key_raw = parsed_url.path.lstrip("/")

                    # 2. **CRITICAL FIX:** URL DECODE the key to pass the literal string to Boto3.
                    s3_key_to_use = unquote_plus(s3_key_raw, encoding="utf-8")

                    # We use the literal, unencoded key for the local filename
                    local_filename = os.path.basename(s3_key_to_use)
                    local_image_path = os.path.join(local_subfolder, local_filename)

                    try:
                        print(
                            f"S3 Key (DECODED for Boto3): Attempting to download image from {s3_key_to_use}"
                        )
                        s3_client.download_file(bucket, s3_key_to_use, local_image_path)
                        print(f"Successfully downloaded image to {local_image_path}")
                    except Exception as e:
                        # Log error and continue. The video creation function will fall back to local/sample image.
                        print(
                            f"WARNING: Failed to download S3 image {s3_key_to_use}. Will proceed with local/fallback images. Error: An error occurred (404) when calling the HeadObject operation: Not Found"
                        )
                        print(f"Original Error Detail: {e}")
            # ---------------------------------------------

            # Define local audio path and download audio
            local_audio_path = os.path.join(
                local_subfolder, os.path.basename(audio_s3_key)
            )
            try:
                s3_client.download_file(bucket, audio_s3_key, local_audio_path)
            except Exception as e:
                # Log the 404 error explicitly as FATAL for this segment
                print(
                    f"FATAL: Failed to download required audio file {audio_s3_key}. Skipping segment. Error: {e}"
                )
                shutil.rmtree(local_subfolder, ignore_errors=True)
                continue  # Skip to next segment

            # Define output path for the intermediate video
            intermediate_video_path = os.path.join(tmp_dir, f"{segment_name}.mp4")

            # Call the main video creation function (passing dynamic config)
            success = create_video_from_images_and_audio(
                local_subfolder,
                local_audio_path,
                intermediate_video_path,
                segment_text,
                is_header_segment=is_header_segment,
                word_chunk_size=word_chunk_size,  # DYNAMIC WORD CHUNK
                target_width=target_width,  # DYNAMIC WIDTH
                target_height=target_height,  # DYNAMIC HEIGHT
            )

            if success:
                intermediate_video_paths.append(intermediate_video_path)
                successful_audio_keys.append(audio_s3_key)  # Record key for archival

            # Clean up local segment files (CRITICAL for /tmp limits).
            shutil.rmtree(local_subfolder, ignore_errors=True)

        # 5. Combine all videos and upload the final result
        if intermediate_video_paths:

            # --- STABLE FADE/CUT TRANSITION IMPLEMENTATION (UPDATED) ---
            final_paths_to_combine = []

            # Interleave the transition video path only if style is 'fade'
            for i, video_path in enumerate(intermediate_video_paths):
                final_paths_to_combine.append(video_path)

                # Add transition unless this is the very last video clip AND the style is 'fade'
                if i < len(intermediate_video_paths) - 1 and transition_style == "fade":
                    final_paths_to_combine.append(TRANSITION_VIDEO_PATH)

            # Define the final output file name
            final_output_file_name = f"{compilation_id}.mp4"
            final_output_file = os.path.join(
                tmp_dir, final_output_file_name
            )  # Store path for cleanup

            # Call the combine_videos function which handles standard concatenation
            combine_videos(final_paths_to_combine, final_output_file)

            # Define the final S3 key
            output_s3_key = f"output_videos/{final_output_file_name}"
            s3_client.upload_file(final_output_file, bucket, output_s3_key)
            print(f"Uploaded final compilation video to s3://{bucket}/{output_s3_key}")

            # ----------------------------------------------------------------
            # 6. ARCHIVAL STEP: Move source audio and JSON manifest
            # ----------------------------------------------------------------

            # Use the ID in the archive path for better traceability
            archive_folder = f"{ARCHIVE_PREFIX}{compilation_id}/"

            # A. Archive the JSON manifest file (e.g., highlights.json)
            print(f"\nArchiving JSON manifest {json_key}...")
            # We add the timestamp to the archived JSON name for safety against reprocessing the same ID
            archive_json_name = f"{os.path.basename(json_key).replace('.json', '')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            new_json_key = os.path.join(archive_folder, archive_json_name)
            move_s3_object(bucket, json_key, new_json_key)

            # B. Archive the successful audio files, preserving sub-folder structure
            print("\nArchiving source audio files...")
            for old_key in successful_audio_keys:
                new_key = os.path.join(archive_folder, old_key)
                move_s3_object(bucket, old_key, new_key)

            print(
                f"Archival complete. New folder structure is s3://{bucket}/{archive_folder}"
            )

            # Final cleanup of all local files (Optimization 2D)
            for path in intermediate_video_paths:
                if os.path.exists(path):
                    os.remove(path)
            if os.path.exists(final_output_file):
                os.remove(final_output_file)
            if os.path.exists(local_json_path):
                os.remove(local_json_path)

            return {
                "statusCode": 200,
                "body": f"Video compilation {compilation_id} created and archived successfully.",
            }
        else:
            # Final cleanup even if no videos were created
            if os.path.exists(local_json_path):
                os.remove(local_json_path)

            return {
                "statusCode": 200,
                "body": "No intermediate videos were successfully created for compilation.",
            }

    except Exception as e:
        print(f"An error occurred in Lambda handler: {e}")

        # Ensure local files are cleaned up even on crash
        if os.path.exists(final_output_file):
            os.remove(final_output_file)
        if os.path.exists(local_json_path):
            os.remove(local_json_path)

        raise
