import argparse
import os
import boto3
import glob

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
from botocore.exceptions import NoCredentialsError

load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)

def convert_text_to_speech(text_segments, fileName="output"):
    # all_audio = []
    previous_text = None

    try:
        for i, segment in enumerate(text_segments):
            print(f"Start converting text: {segment}")
            audio = elevenlabs.text_to_speech.convert(
                text=segment,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                previous_text=previous_text,
                next_text=text_segments[i+1] if i + 1 < len(text_segments) else None
            )
            # all_audio.append(audio)
            previous_text = segment
            save(audio, f'{fileName}-{i}.mp3')
            print(f"Audio saved as {fileName}-{i}.mp3")

        # for j, audio_segment in enumerate(all_audio):
        #     save(audio_segment, f'{fileName}-{j}.mp3')
        #     print(f"Audio saved as {fileName}-{j}.mp3")

    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert "{text_segments}" to speech.')
        raise e

def upload_file_to_s3(fileName):
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name='ap-southeast-2'
    )
    bucketName = "adien-apac-practice-bucket"
    audio_files = glob.glob(f"{fileName}*.mp3")

    try:
        for audioFileName in audio_files:
            key = f"audio/{audioFileName}"
            s3.upload_file(audioFileName, bucketName, key)
            print(f"File {audioFileName} uploaded to {bucketName}/{key}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except Exception as e:
        print(f"Error uploading file: {e}")

text_segments = [
    "The quick brown fox jumps over the lazy dog.",
    "This is a second sentence to demonstrate continuity.",
    "And finally, a third sentence to complete the example."
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert text to speech and upload to S3.")
    parser.add_argument("--text", type=str, default=text_segments, help="Text to convert to speech")
    parser.add_argument("--output", type=str, default="output", help="Output MP3 file name")
    args = parser.parse_args()

    convert_text_to_speech(args.text, args.output)
    upload_file_to_s3(args.output)