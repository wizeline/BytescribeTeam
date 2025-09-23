import os
import sys
from natsort import natsorted
from moviepy import *
from PIL import Image

# Explicitly set ffmpeg path for moviepy
# import moviepy.config as mpy_config

# mpy_config.FFMPEG_BINARY = "/opt/homebrew/bin/ffmpeg"


def create_video_from_images_and_audio(
    image_folder: str, audio_path: str, output_path: str, fps: int = 1
):
    """
    Creates a video from a sequence of images in a specified folder and an audio file.

    Args:
        image_folder (str): The path to the folder containing the images.
        audio_path (str): The path to the audio file.
        output_path (str): The desired path for the final video file.
        fps (int): Frames per second for the video.
    """
    if not os.path.isdir(image_folder):
        print(f"Error: The specified image folder '{image_folder}' does not exist.")
        return
    if not os.path.isfile(audio_path):
        print(f"Error: The specified audio file '{audio_path}' does not exist.")
        return

    # Get a list of all image files in the folder and sort them naturally.
    image_files = [
        os.path.join(image_folder, img)
        for img in os.listdir(image_folder)
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if not image_files:
        print(f"Error: No image files found in '{image_folder}'.")
        return

    image_files = natsorted(image_files)
    print(f"Found {len(image_files)} images. Creating video...")

    try:
        # Step 1: Load the audio clip to get its duration.
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        # Step 2: Calculate the duration for each image.
        num_images = len(image_files)
        if num_images == 0:
            print("Error: No images found.")
            return

        image_duration = audio_duration / num_images
        print(f"Each image will be shown for {image_duration:.2f} seconds.")

        # Step 3: Create a video clip from the image sequence with the calculated duration.
        clips = [ImageClip(path, duration=image_duration) for path in image_files]
        video_clip = concatenate_videoclips(clips, method="compose")

        # Step 4: Set the audio to the video.
        video_clip.audio = audio_clip

        # Step 5: Write the video file.
        video_clip.write_videofile(
            output_path, fps=fps, codec="libx264", audio_codec="aac"
        )
        print(f"Video successfully created at {output_path}")

    except Exception as e:
        print(f"An error occurred during video creation: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_video.py <image_folder> <audio_file>")
        sys.exit(1)
    else:
        image_folder_path = sys.argv[1]
        audio_file_path = sys.argv[2]
        output_video_file = "output_video.mp4"
        create_video_from_images_and_audio(
            image_folder_path, audio_file_path, output_video_file
        )
