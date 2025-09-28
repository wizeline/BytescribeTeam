import os
import boto3
from natsort import natsorted
from urllib.parse import unquote_plus
from moviepy import *
import moviepy.config as mpy_config
import shutil
from datetime import datetime

# --- GLOBAL CONFIGURATION (Safe and Stable) ---

# Initialize the S3 client globally
s3_client = boto3.client("s3")
# Initialize Lambda's temporary directory globally
tmp_dir = "/tmp"

# Explicitly set ffmpeg path (relies on copy in lambda_handler)
mpy_config.FFMPEG_BINARY = os.path.join(tmp_dir, "ffmpeg")

# Define the archive prefix globally
ARCHIVE_PREFIX = "processed-input/"


# --- UTILITY FUNCTION: S3 Prefix Move ---


def move_s3_prefix(bucket, old_prefix, new_prefix):
    """
    Moves all objects from old_prefix to new_prefix within the same bucket
    via copy and delete operations.
    """
    s3_paginator = s3_client.get_paginator("list_objects_v2")

    print(f"Starting archive move from {old_prefix} to {new_prefix}")

    # List all objects under the old prefix
    for page in s3_paginator.paginate(Bucket=bucket, Prefix=old_prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            old_key = obj["Key"]
            # Determine the new key by replacing the old prefix
            new_key = old_key.replace(old_prefix, new_prefix, 1)

            # 1. Copy the object
            s3_client.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": old_key},
                Key=new_key,
            )

            # 2. Delete the original object
            s3_client.delete_object(Bucket=bucket, Key=old_key)

    print(f"Successfully archived objects from {old_prefix} to {new_prefix}")


# --- CORE FUNCTIONS ---


def combine_videos(video_paths: list, final_output_path: str):
    """
    Combines a list of video files into a single final video.
    Includes environment overrides for FFmpeg safety.
    """
    print(f"Combining {len(video_paths)} videos into {final_output_path}...")

    if not video_paths:
        print("No videos to combine. Skipping final step.")
        return

    # --- CRITICAL FIX: RE-INJECT ENVIRONMENT OVERRIDES ---
    # Ensures subprocesses (FFmpeg) use /tmp and do not hit Read-only error.
    os.environ["TMPDIR"] = tmp_dir
    os.environ["TEMP"] = tmp_dir
    os.environ["TMP"] = tmp_dir

    # Temporarily change the current working directory (CWD) to /tmp
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    # ----------------------------------------------------

    try:
        # Load all clips from the list of paths
        clips = [VideoFileClip(path) for path in video_paths]

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
        # Explicitly close all clips to free up resources
        if "clips" in locals():
            for clip in clips:
                clip.close()
        if "final_clip" in locals():
            final_clip.close()


def create_video_from_images_and_audio(
    image_folder: str, audio_path: str, output_path: str, fps: int = 1
):
    """
    Creates a video from a sequence of images and a single audio file from local paths.
    """
    if not os.path.isdir(image_folder):
        print(f"Error: The specified image folder '{image_folder}' does not exist.")
        return False
    if not os.path.isfile(audio_path):
        print(f"Error: The specified audio file '{audio_path}' does not exist.")
        return False

    # Get a list of all image files in the folder and sort them naturally.
    image_files = [
        os.path.join(image_folder, img)
        for img in os.listdir(image_folder)
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if not image_files:
        print(f"Error: No image files found in '{image_folder}'.")
        return False

    image_files = natsorted(image_files)
    print(f"Found {len(image_files)} images. Creating video...")

    # --- CWD OVERRIDE FOR SUBPROCESS SAFETY (Maintains the writable environment) ---
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    # ------------------------------------------------------------

    try:
        # Step 1: Load the audio clip to get its duration.
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # Step 2: Calculate the duration for each image.
        num_images = len(image_files)
        if num_images == 0:
            return False

        image_duration = audio_duration / num_images
        print(f"Each image will be shown for {image_duration:.2f} seconds.")

        # Step 3: Create a video clip from the image sequence.
        clips = [ImageClip(path, duration=image_duration) for path in image_files]
        video_clip = concatenate_videoclips(clips, method="compose")

        # Step 4: Set the audio to the video.
        video_clip.audio = audio_clip

        # Step 5: Write the video file.
        video_clip.write_videofile(
            output_path, fps=fps, codec="libx264", audio_codec="aac"
        )
        print(f"Video successfully created at {output_path}")
        return True  # Return True on success

    except Exception as e:
        print(f"An error occurred during video creation: {e}")
        raise

    finally:
        # Restore the original working directory
        os.chdir(original_cwd)


# --- UPDATED LAMBDA HANDLER ---
def lambda_handler(event, context):
    print("Received S3 event:", event)

    # --- CRITICAL FIX: FFmpeg Binary Setup ---
    try:
        ffmpeg_source = "/var/task/ffmpeg"
        ffmpeg_dest = os.path.join(tmp_dir, "ffmpeg")
        if not os.path.exists(ffmpeg_dest):
            shutil.copy(ffmpeg_source, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)  # Ensure it's executable
    except Exception as e:
        print(f"FATAL: Failed to copy or set permissions for FFmpeg: {e}")
        raise

    try:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"], encoding="utf-8")

        # 1. Determine the parent prefix (e.g., 'test-compilation/' from 'test-compilation/segment_01/audio.mp3')
        parent_prefix = os.path.dirname(os.path.dirname(key))
        if parent_prefix and parent_prefix[-1] != "/":
            parent_prefix += "/"

        # Handle case where the prefix is empty (files are in the bucket root)
        if parent_prefix == "/":
            parent_prefix = ""

        # 2. Find all immediate sub-folders (segment prefixes)
        s3_paginator = s3_client.get_paginator("list_objects_v2")
        sub_prefixes = set()

        # List to track which prefixes were SUCCESSFULLY processed for archival
        successful_prefixes = []

        # This lists prefixes immediately under the determined parent_prefix
        for page in s3_paginator.paginate(
            Bucket=bucket, Prefix=parent_prefix, Delimiter="/"
        ):
            if "CommonPrefixes" in page:
                for prefix_data in page["CommonPrefixes"]:
                    sub_prefixes.add(prefix_data["Prefix"])

        if not sub_prefixes:
            print(
                f"No segment sub-folders found under prefix: {parent_prefix}. Exiting."
            )
            return {"statusCode": 200, "body": "No video sub-folders to process."}

        local_videos_to_combine = []

        # 3. Loop through each segment sub-folder
        for video_prefix in natsorted(list(sub_prefixes)):
            subfolder_name = os.path.basename(video_prefix.strip("/"))
            print(f"\n--- Starting processing for segment: {subfolder_name} ---")

            # Create local folder for the segment files
            local_subfolder = os.path.join(tmp_dir, subfolder_name)
            os.makedirs(local_subfolder, exist_ok=True)

            sub_objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=video_prefix)
            local_audio_path = None

            # Download all files in the segment folder
            for obj in sub_objects.get("Contents", []):
                obj_key = obj["Key"]

                # Skip the folder key itself
                if obj_key == video_prefix:
                    continue

                local_path = os.path.join(local_subfolder, os.path.basename(obj_key))

                # Download audio file (setting local_audio_path)
                if obj_key.lower().endswith((".mp3", ".wav")):
                    s3_client.download_file(bucket, obj_key, local_path)
                    local_audio_path = local_path
                # Download image file
                elif obj_key.lower().endswith((".png", ".jpg", ".jpeg")):
                    s3_client.download_file(bucket, obj_key, local_path)

            if not local_audio_path:

                print(f"Skipping {subfolder_name}: No audio file found in segment.")
                continue

            # Define output path for the intermediate video
            intermediate_video_path = os.path.join(tmp_dir, f"{subfolder_name}.mp4")

            # Call the main video creation function
            success = create_video_from_images_and_audio(
                local_subfolder, local_audio_path, intermediate_video_path
            )

            if success:
                local_videos_to_combine.append(intermediate_video_path)
                successful_prefixes.append(video_prefix)  # Record prefix for archiving

            # Clean up local segment files (CRITICAL for /tmp limits)
            shutil.rmtree(local_subfolder)
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)

        # 4. Combine all videos and upload the final result
        if local_videos_to_combine:
            final_output_file_name = "final_video.mp4"
            final_output_file = os.path.join(tmp_dir, final_output_file_name)
            combine_videos(local_videos_to_combine, final_output_file)

            # Define the final S3 key at the root of the designated prefix
            output_s3_key = f"output_videos/{final_output_file_name}"

            s3_client.upload_file(final_output_file, bucket, output_s3_key)

            print(f"Uploaded final compilation video to s3://{bucket}/{output_s3_key}")

            # ----------------------------------------------------------------
            # 5. ARCHIVAL STEP: Move source files to 'processed-input/'
            # ----------------------------------------------------------------
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            for prefix in successful_prefixes:
                # The segment name is the folder name (e.g., 'segment_01/')
                segment_folder_name = os.path.basename(prefix.strip("/"))

                # New prefix: processed-input/20250927123456-segment_01/
                new_segment_prefix = (
                    f"{ARCHIVE_PREFIX}{timestamp}-{segment_folder_name}/"
                )

                # Call the utility to move contents of the prefix
                move_s3_prefix(bucket, prefix, new_segment_prefix)

            # Final cleanup of intermediate local video files
            for path in local_videos_to_combine:
                if os.path.exists(path):
                    os.remove(path)
            os.remove(final_output_file)

            return {
                "statusCode": 200,
                "body": "Video compilation created, uploaded, and source files archived successfully.",
            }
        else:
            return {
                "statusCode": 200,
                "body": "No intermediate videos were successfully created for compilation.",
            }

    except Exception as e:
        print(f"An error occurred in Lambda handler: {e}")
        raise
