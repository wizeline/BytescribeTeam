import argparse
import os
import boto3

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
from botocore.exceptions import NoCredentialsError

print('Loading function')
load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)

def convert_text_to_speech(text, fileName="output.mp3"):
    print(f"Start converting text: {text}")
    try:
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        print(f"Audio generated, saving to {fileName}...")
        save(audio, fileName)
        print(f"Audio saved as {fileName}")
    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert "{text}" to speech.')
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
    try:
        s3.upload_file(fileName, bucketName, fileName)
        print(f"File {fileName} uploaded to {bucketName}/{fileName}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except Exception as e:
        print(f"Error uploading file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert text to speech and upload to S3.")
    parser.add_argument("text", type=str, help="Text to convert to speech")
    parser.add_argument("--output", type=str, default="output.mp3", help="Output MP3 file name")
    args = parser.parse_args()

    convert_text_to_speech(args.text, args.output)
    upload_file_to_s3(args.output)