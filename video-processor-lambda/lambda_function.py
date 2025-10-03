import os
import boto3
import glob
import json
import shutil
from natsort import natsorted
from urllib.parse import unquote_plus

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

# Functional effects (Included for completeness but no longer used for transitions)
from moviepy.video.fx import FadeIn, FadeOut

import moviepy.config as mpy_config
from datetime import datetime
import random

# --- GLOBAL CONFIGURATION (Safe and Stable) ---

# Initialize the S3 client globally
s3_client = boto3.client("s3")
# Initialize Lambda's temporary directory globally
tmp_dir = "/tmp"

# Explicitly set ffmpeg path (relies on copy in lambda_handler)
mpy_config.FFMPEG_BINARY = os.path.join(tmp_dir, "ffmpeg")

# Define the fallback image directory
FALLBACK_IMAGE_DIR = "/var/task/images"

# Define the archive prefix globally
ARCHIVE_PREFIX = "processed-input/"

# Target video resolution
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080

# --- STABLE TRANSITION PATH RESTORED ---
TRANSITION_VIDEO_PATH = "/var/task/fade_transition.mp4"


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


# --- CORE FUNCTION: COMBINE VIDEOS (REVERTED) ---


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


# --- UTILITY FUNCTION: DYNAMIC SUBTITLE GENERATOR (Punctuation-Based Chunking) ---


def generate_timed_text_clips(
    text: str, duration: float, font_path: str, max_words_per_chunk: int = 4
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


# --- UTILITY FUNCTION: IMAGE RESIZE AND CROP (Final API Fix) ---


def resize_and_crop_image(
    image_path: str, target_width: int, target_height: int, output_path: str = None
) -> str:
    """
    Resizes and center-crops an image to the target resolution (e.g., 1920x1080).
    Uses the direct object methods (.cropped() and .resized()) for compatibility.
    Saves the result to output_path or overwrites the input file if output_path is None.
    Returns the path to the resulting image file.
    """
    original_clip = None
    # Use the provided output_path or default to overwriting the input image
    final_output_path = output_path if output_path else image_path

    try:
        original_clip = ImageClip(image_path)
        width, height = original_clip.size
        target_ratio = target_width / target_height
        current_ratio = width / height
        cropped_clip = original_clip  # Initialize cropped_clip

        # --- Start Image Processing ---
        print(
            f"Processing image: {os.path.basename(image_path)}. Original size: {width}x{height}."
        )

        # 1. Cropping Logic
        if abs(current_ratio - target_ratio) < 0.01:
            # Check for near 16:9 - no crop needed
            print("Image is already near 16:9 ratio. No crop needed.")
        elif current_ratio > target_ratio:
            # Image is wider (e.g., 21:9). Crop width to match target height.
            new_width = int(height * target_ratio)
            x_offset = (width - new_width) // 2

            # --- Use .cropped(x1, x2) ---
            cropped_clip = original_clip.cropped(
                x1=x_offset, x2=x_offset + new_width, y1=0, y2=height
            )
            print(f"Cropping width from {width} to {new_width}.")
        else:
            # Image is taller (e.g., 4:3). Crop height to match target width.
            new_height = int(width / target_ratio)
            y_offset = (height - new_height) // 2

            # --- Use .cropped(y1, y2) ---
            cropped_clip = original_clip.cropped(
                y1=y_offset, y2=y_offset + new_height, x1=0, x2=width
            )
            print(f"Cropping height from {height} to {new_height}.")

        # 2. Resize to exact target dimensions
        # --- Use .resized(width, height) ---
        resized_clip = cropped_clip.resized(width=target_width, height=target_height)

        # 3. Save the resized image (Overwrites the original/copied file)
        if final_output_path.lower().endswith((".jpg", ".jpeg")):
            resized_clip.save_frame(final_output_path)
        else:
            # Default to PNG
            final_output_path = final_output_path.rsplit(".", 1)[0] + ".png"
            resized_clip.save_frame(final_output_path)

        print(f"Successfully resized and saved to {final_output_path}")
        return final_output_path

    except Exception as e:
        print(f"WARNING: Image processing failed for {image_path}. Error: {e}")
        return image_path

    finally:
        if original_clip:
            original_clip.close()


# --- CORE FUNCTION: COMBINE VIDEOS (Reverted to standard concatenation) ---


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


# --- CORE FUNCTION: CREATE VIDEO (STABLE BASELINE) ---


def create_video_from_images_and_audio(
    image_folder: str,
    audio_path: str,
    output_path: str,
    segment_text: str,
    fps: int = 1,
):
    """
    Creates a video from a sequence of images and a single audio file from local paths.
    Pads the video duration to a minimum of 1.0s.
    Fades have been removed to return to a stable baseline.
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

    # --- IMAGE SELECTION AND PROCESSING LOGIC ---
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

        # *** os.path.join ***
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
            current_path, TARGET_WIDTH, TARGET_HEIGHT, output_path=current_path
        )
        final_image_paths.append(resized_path)

    image_files = final_image_paths
    # --- END IMAGE SELECTION AND PROCESSING LOGIC ---

    print(f"Content duration: {video_segment_duration:.2f}s.")

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

        subtitle_clips = generate_timed_text_clips(
            segment_text, video_segment_duration, font_file, max_words_per_chunk=4
        )

        positioned_subtitle_clips = []
        for clip in subtitle_clips:
            clip = clip.with_position(("center", video_clip.h * 0.9))
            positioned_subtitle_clips.append(clip)
        # --- END DYNAMIC SUBTITLE LOGIC ---

        # 4. BUILD THE FINAL COMPOSITE CLIP (No Fades Applied)
        video_clip_edit = CompositeVideoClip(
            [video_clip] + positioned_subtitle_clips, size=video_clip.size
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
            ffmpeg_params=["-vf", "scale=1920:1080", "-pix_fmt", "yuv420p"],
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


# --- FINAL LAMBDA HANDLER (RE-IMPLEMENTED BLACK TRANSITION) ---


def lambda_handler(event, context):
    print("Received event:", event)

    # --- FFmpeg Binary Setup ---
    try:
        ffmpeg_source = "/var/task/ffmpeg"
        ffmpeg_dest = os.path.join(tmp_dir, "ffmpeg")
        if not os.path.exists(ffmpeg_dest):
            shutil.copy(ffmpeg_source, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)  # Ensure it's executable
    except Exception as e:
        print(f"FATAL: Failed to copy or set permissions for FFmpeg: {e}")
        raise

    # Store a variable for the compilation ID, initialized to a fallback value
    compilation_id = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        # 1. Determine Bucket and Key (Assuming S3 trigger on highlights.json)
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        json_key = unquote_plus(record["s3"]["object"]["key"], encoding="utf-8")

        print(f"Processing JSON manifest from s3://{bucket}/{json_key}")

        # 2. Download and Parse highlights.json
        local_json_path = os.path.join(tmp_dir, os.path.basename(json_key))
        s3_client.download_file(bucket, json_key, local_json_path)

        with open(local_json_path, "r") as f:
            full_manifest = json.load(f)

        # --- EXTRACT ID FOR FILENAME ---
        compilation_id = full_manifest.get("id", compilation_id)
        highlights_data = full_manifest.get("highlights", [])
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

            # NEW: Extract the segment text, using a fallback if missing
            segment_text = segment.get("text", "No Text Provided")

            # --- GET IMAGE S3 KEY ---
            image_data = segment.get("image", {})
            image_s3_key = image_data.get("s3_key")
            # -----------------------------

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

            # --- S3 IMAGE DOWNLOAD ---
            if image_s3_key:
                # FIX APPLIED: Decode the S3 key before using it for download
                decoded_image_s3_key = unquote_plus(image_s3_key, encoding="utf-8")
                print(
                    f"S3_KEY found: Attempting to download image from {decoded_image_s3_key}"
                )

                # Use the base name of the DECODED S3 key as the local filename
                local_image_path = os.path.join(
                    local_subfolder, os.path.basename(decoded_image_s3_key)
                )
                try:
                    s3_client.download_file(
                        bucket, decoded_image_s3_key, local_image_path
                    )
                    print(f"Successfully downloaded image to {local_image_path}")
                except Exception as e:
                    # Log error and continue. The video creation function will fall back to local/sample image.
                    print(
                        f"WARNING: Failed to download S3 image {decoded_image_s3_key}. Will proceed with local/fallback images. Error: {e}"
                    )
            # -------------------------------------

            # Define local audio path and download audio
            local_audio_path = os.path.join(
                local_subfolder, os.path.basename(audio_s3_key)
            )
            try:
                s3_client.download_file(bucket, audio_s3_key, local_audio_path)
            except Exception as e:
                print(
                    f"FATAL: Failed to download required audio file {audio_s3_key}. Skipping segment. Error: {e}"
                )
                shutil.rmtree(local_subfolder, ignore_errors=True)
                continue

            # Define output path for the intermediate video
            intermediate_video_path = os.path.join(tmp_dir, f"{segment_name}.mp4")

            # Call the main video creation function (now passing segment_text)
            success = create_video_from_images_and_audio(
                local_subfolder, local_audio_path, intermediate_video_path, segment_text
            )

            if success:
                intermediate_video_paths.append(intermediate_video_path)
                successful_audio_keys.append(audio_s3_key)  # Record key for archival

            # Clean up local segment files (CRITICAL for /tmp limits).
            shutil.rmtree(local_subfolder, ignore_errors=True)

        # 5. Combine all videos and upload the final result
        if intermediate_video_paths:

            # --- STABLE FADE TRANSITION IMPLEMENTATION ---
            final_paths_to_combine = []

            # Interleave the black transition video path after every segment except the last one
            for i, video_path in enumerate(intermediate_video_paths):
                final_paths_to_combine.append(video_path)

                # Add transition unless this is the very last video clip
                if i < len(intermediate_video_paths) - 1:
                    final_paths_to_combine.append(TRANSITION_VIDEO_PATH)

            # Define the final output file name
            final_output_file_name = f"{compilation_id}.mp4"
            final_output_file = os.path.join(tmp_dir, final_output_file_name)

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

            # Final cleanup of all local files
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
            return {
                "statusCode": 200,
                "body": "No intermediate videos were successfully created for compilation.",
            }

    except Exception as e:
        print(f"An error occurred in Lambda handler: {e}")
        raise
