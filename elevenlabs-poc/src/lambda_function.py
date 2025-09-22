import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
import boto3
from botocore.exceptions import NoCredentialsError

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
        print(f'Audio generated, saving to "/tmp/{fileName}..."')
        save(audio, f'/tmp/{fileName}')
        print(f'Audio saved as "/tmp/{fileName}"')
    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert "{text}" to speech.')
        raise e

def upload_file_to_s3(fileName):
    s3 = boto3.client('s3')
    bucketName = "adien-apac-practice-bucket"
    try:
        s3.upload_file(f'/tmp/{fileName}', bucketName, fileName)
        print(f'File /tmp/{fileName} uploaded to {bucketName}/{fileName}')
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except Exception as e:
        print(f"Error uploading file: {e}")

def lambda_handler(event, context):
    text = event.get("text", "Hello from Lambda!")
    output_filename = event.get("output", "output.mp3")

    convert_text_to_speech(text, output_filename)
    upload_file_to_s3(output_filename)
    return {
        "statusCode": 200,
        "body": f"Audio file '{output_filename}' uploaded to s3 bucket."
    }
