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

def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }

def _proxy_response(status_code: int, payload: dict):
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(payload),
    }

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
    folderName = fileName
    try:
        audio_files = glob.glob(f"/tmp/{fileName}*.mp3")
        for audioFileName in audio_files:
            key = audioFileName.replace("/tmp/", "")
            s3.upload_file(audioFileName, bucketName, f"{folderName}/{key}")
            print(f"File {audioFileName} uploaded to {bucketName}/{folderName}/{key}")
    except FileNotFoundError:
        print("The file was not found")
        raise e
    except NoCredentialsError:
        print("Credentials not available")
        raise e
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise e

def lambda_handler(event, context):
    # Handle preflight from browsers
    if isinstance(event, dict) and event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}

    highlights = event.get("highlights", [])
    for item in highlights:
        if not item.get("text"):
            return {
                "statusCode": 400,
                "body": f"Invalid text: {item}"
            }

    text_segments = list(map(lambda item: item["text"], highlights))
    output_folder = event.get("output", "output")
    if not text_segments:
        return {
            "statusCode": 400,
            "body": "No text is found."
        }

    try:
        convert_text_to_speech(text_segments, output_folder)
        upload_file_to_s3(output_folder)
        return {
            "statusCode": 200,
            "body": f"Audio files uploaded to s3 bucket folder: '{output_folder}'"
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "error": "Sorry, something went wrong.",
            "message": e
        }
