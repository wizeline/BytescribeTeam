import json
import os
import time
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
import boto3
from botocore.exceptions import NoCredentialsError

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)
voiceId = os.getenv("ELEVENLABS_VOICE_ID")
modelId = os.getenv("ELEVENLABS_MODEL_ID")


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


def convert_text_to_speech(text_segments, fileName="audio"):
    all_audio = []
    try:
        for segment in text_segments:
            print(f"Start converting text: {segment}")
            audio = elevenlabs.text_to_speech.convert(
                text=segment,
                voice_id=voiceId,
                model_id=modelId,
                output_format="mp3_44100_128",
            )
            all_audio.append(audio)

        for j, audio_segment in enumerate(all_audio):
            save(audio_segment, f"/tmp/{fileName}{j + 1}.mp3")
            print(f"Audio saved as /tmp/{fileName}{j + 1}.mp3")
    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert "{text_segments}" to speech.')
        raise e


def upload_file_to_s3(id, fileName, data):
    s3 = boto3.client("s3")
    bucketName = os.getenv("DESTINATION_BUCKET")
    folderName = fileName
    result = []

    try:
        for i, highlight in enumerate(data):
            s3.upload_file(
                f"/tmp/audio{i + 1}.mp3",
                bucketName,
                f"input/{folderName}{i + 1}/audio{i + 1}.mp3",
            )
            print(
                f"File /tmp/audio{i + 1}.mp3 uploaded to input/{folderName}{i + 1}/audio{i + 1}.mp3"
            )
            result.append(
                {
                    "order": highlight["order"],
                    "text": highlight["text"],
                    "image": highlight["image"],
                    "audio": f"input/{folderName}{i + 1}/audio{i + 1}.mp3",
                }
            )

        # json file
        s3.put_object(
            Bucket=bucketName,
            Key="input/highlights.json",
            Body=json.dumps({"id": id, "highlights": result}),
            ContentType="application/json",
        )
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
            return _proxy_response(400, {"error": f"Invalid text: {item}"})

    text_segments = list(map(lambda item: item["text"], highlights))
    output_filename = event.get("output", "highlight")
    if not text_segments:
        return _proxy_response(400, {"error": "No text is found."})

    current_datetime = f"{int(time.time()*1000)}"
    try:
        convert_text_to_speech(text_segments)
        upload_file_to_s3(current_datetime, output_filename, highlights)
        return {
            "statusCode": 200,
            "body": {
                "id": current_datetime,
            },
        }
    except Exception as e:
        return _proxy_response(500, {"error": f"Sorry, something went wrong. {str(e)}"})
