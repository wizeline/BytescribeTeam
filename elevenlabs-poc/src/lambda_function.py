import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
import boto3
from botocore.exceptions import NoCredentialsError
import glob

load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)

def convert_text_to_speech(text_segments, fileName="output"):
    all_audio = []
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
            all_audio.append(audio)
            previous_text = segment
            # save(audio, f'/tmp/{fileName}-{i}.mp3')
            # print(f"Audio saved as /tmp/{fileName}-{i}.mp3")

        for j, audio_segment in enumerate(all_audio):
            save(audio_segment, f'/tmp/{fileName}-{j}.mp3')
            print(f"Audio saved as /tmp/{fileName}-{j}.mp3")
    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert "{text_segments}" to speech.')
        raise e

def upload_file_to_s3(fileName):
    s3 = boto3.client('s3')
    bucketName = "adien-apac-practice-bucket"
    try:
        audio_files = glob.glob(f"/tmp/{fileName}*.mp3")
        for audioFileName in audio_files:
            key = f"audio/{audioFileName}"
            s3.upload_file(f'/tmp/{audioFileName}', bucketName, key)
            print(f"File /tmp/{audioFileName} uploaded to {bucketName}/{key}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except Exception as e:
        print(f"Error uploading file: {e}")

def lambda_handler(event, context):
    text = event.get("text", ["Hello from Lambda!"])
    output_filename = event.get("output", "output")

    convert_text_to_speech(text, output_filename)
    upload_file_to_s3(output_filename)
    return {
        "statusCode": 200,
        "body": f"Audio file '{output_filename}' uploaded to s3 bucket."
    }
