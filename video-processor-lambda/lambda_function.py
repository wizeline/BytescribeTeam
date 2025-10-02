import os
import boto3
import glob
import json
import shutil
from natsort import natsorted
from urllib.parse import unquote_plus

# Assuming moviepy and its dependencies are included in the Lambda layer or package
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    ColorClip,
)

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


# --- UTILITY FUNCTION: S3 Object Move ---


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


# --- CORE FUNCTION: COMBINE VIDEOS ---


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


# --- CORE FUNCTION: CREATE VIDEO (WITH DIRECT DURATION ASSIGNMENT) ---


def create_video_from_images_and_audio(
    image_folder: str, audio_path: str, output_path: str, fps: int = 1
):
    """
    Creates a video from a sequence of images and a single audio file from local paths.
    Pads the video duration to a minimum of 1.0s if the audio is too short.
    """
    if not os.path.isfile(audio_path):
        print(f"Error: The specified audio file '{audio_path}' does not exist.")
        return False

    # --- IMAGE SELECTION LOGIC ---
    # 1. Check for images in the segment's dedicated local folder (where S3 download put it)
    local_image_files = [
        os.path.join(image_folder, img)
        for img in os.listdir(image_folder)
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    image_files = natsorted(local_image_files)
    image_source = image_folder

    if not image_files:
        print(
            f"Warning: No images found in '{image_folder}'. Falling back to a SINGLE, RANDOM sample image."
        )

        # 2. Fallback to a single, random sample image
        fallback_images = glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.png"))
        fallback_images.extend(glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.jpg")))
        fallback_images.extend(glob.glob(os.path.join(FALLBACK_IMAGE_DIR, "*.jpeg")))

        if fallback_images:
            random_image_path = random.choice(fallback_images)
            image_files = [random_image_path]
            image_source = f"RANDOM image: {os.path.basename(random_image_path)}"
        else:
            image_files = []

    if not image_files:
        print(
            f"Error: No images found and no sample images found in '{FALLBACK_IMAGE_DIR}'. Skipping segment."
        )
        return False
    # -----------------------------

    print(f"Using {len(image_files)} image(s) from '{image_source}'. Creating video...")

    # --- CWD OVERRIDE FOR SUBPROCESS SAFETY ---
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    # ----------------------------------------

    audio_clip = None
    video_clip = None
    clips = []

    try:
        # Step 1: Load the audio clip and determine segment duration.
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # --- PADDING LOGIC ---
        MIN_ENCODE_DURATION = 1.0

        if audio_duration < MIN_ENCODE_DURATION:
            print(
                f"Warning: Audio duration ({audio_duration:.2f}s) is too short. Padding video duration to {MIN_ENCODE_DURATION}s for stable encoding."
            )
            video_segment_duration = MIN_ENCODE_DURATION

        else:
            video_segment_duration = audio_duration
        # ---------------------------------------

        # Step 2: Calculate the duration for each image based on the final video duration.
        num_images = len(image_files)
        image_duration = video_segment_duration / num_images

        print(f"Each image will be shown for {image_duration:.2f} seconds.")

        # Step 3: Create and concatenate image clips.
        clips = [ImageClip(path, duration=image_duration) for path in image_files]

        # Assign concatenation result first.
        video_clip = concatenate_videoclips(clips, method="compose")

        # Assign duration directly to the attribute to bypass unsupported method.
        video_clip.duration = video_segment_duration

        # Step 4: Set the audio.
        video_clip.audio = audio_clip

        # Step 5: Write the video file.
        video_clip.write_videofile(
            output_path, fps=fps, codec="libx264", audio_codec="aac"
        )
        print(f"Video successfully created at {output_path}")
        return True

    except Exception as e:
        print(f"An error occurred during video creation: {e}")
        raise

    finally:
        os.chdir(original_cwd)
        if audio_clip:
            audio_clip.close()
        if video_clip:
            video_clip.close()
        if clips:
            for clip in clips:
                clip.close()


# --- FINAL LAMBDA HANDLER ---


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

        local_videos_to_combine = []
        successful_audio_keys = []  # List to track S3 keys to archive

        # 4. Loop through each ordered segment
        for i, segment in enumerate(highlights_data):
            order = segment.get("order", i)
            audio_s3_key = segment.get("audio")

            # --- NEW: GET IMAGE S3 KEY ---
            image_data = segment.get("image", {})
            image_s3_key = image_data.get("s3_key")
            # -----------------------------

            segment_name = f"segment_{order:03d}"

            print(
                f"\n--- Starting processing for segment: {segment_name} (Order {order}) ---"
            )

            if not audio_s3_key:
                print(f"Skipping segment {order}: 'audio' key missing.")
                continue

            # --- PREPARE LOCAL FOLDERS & PATHS ---
            local_subfolder = os.path.join(tmp_dir, segment_name)
            os.makedirs(local_subfolder, exist_ok=True)

            # --- NEW LOGIC: S3 IMAGE DOWNLOAD ---
            if image_s3_key:
                print(f"S3_KEY found: Attempting to download image from {image_s3_key}")
                # Use the base name of the S3 key as the local filename
                local_image_path = os.path.join(
                    local_subfolder, os.path.basename(image_s3_key)
                )
                try:
                    s3_client.download_file(bucket, image_s3_key, local_image_path)
                    print(f"Successfully downloaded image to {local_image_path}")
                except Exception as e:
                    # Log error and continue. The video creation function will fall back to local/sample image.
                    print(
                        f"WARNING: Failed to download S3 image {image_s3_key}. Will proceed with local/fallback images. Error: {e}"
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

            # Call the main video creation function (now with direct duration assignment)
            # This function automatically picks up the S3-downloaded image if it exists in local_subfolder
            success = create_video_from_images_and_audio(
                local_subfolder, local_audio_path, intermediate_video_path
            )

            if success:
                local_videos_to_combine.append(intermediate_video_path)
                successful_audio_keys.append(audio_s3_key)  # Record key for archival

            # Clean up local segment files (CRITICAL for /tmp limits)
            shutil.rmtree(local_subfolder, ignore_errors=True)

        # 5. Combine all videos and upload the final result
        if local_videos_to_combine:
            # --- UPDATED FILENAME HERE ---
            final_output_file_name = f"{compilation_id}.mp4"
            final_output_file = os.path.join(tmp_dir, final_output_file_name)

            combine_videos(local_videos_to_combine, final_output_file)

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
            for path in local_videos_to_combine:
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
