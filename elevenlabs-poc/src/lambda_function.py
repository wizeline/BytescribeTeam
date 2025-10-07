import json
import os
import time
import uuid
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import save
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)
voiceId = os.getenv("ELEVENLABS_VOICE_ID")
modelId = os.getenv("ELEVENLABS_MODEL_ID")

s3 = boto3.client("s3")
bucketName = os.getenv("DESTINATION_BUCKET")


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


def upload_file_to_s3(id, data):
    result = []

    try:
        for i, highlight in enumerate(data):
            s3.upload_file(
                f"/tmp/audio{i + 1}.mp3",
                bucketName,
                f"input/highlight{i + 1}/audio{i + 1}.mp3",
            )
            print(
                f"File /tmp/audio{i + 1}.mp3 uploaded to s3 bucket: input/highlight{i + 1}/audio{i + 1}.mp3"
            )
            result.append(
                {
                    "order": highlight["order"],
                    "text": highlight["text"],
                    "image": highlight["image"],
                    "audio": f"input/highlight{i + 1}/audio{i + 1}.mp3",
                }
            )

        # json file
        s3.put_object(
            Bucket=bucketName,
            Key="input/highlights.json",
            Body=json.dumps({"id": id, "highlights": result}),
            ContentType="application/json",
        )
        print(f"File highlights.json uploaded to s3 bucket: input/highlights.json")
    except FileNotFoundError:
        print("The file was not found")
        raise e
    except NoCredentialsError:
        print("Credentials not available")
        raise e
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise e


def _process_async_job(event, context):
    try:
        body_str = event.get("body", "{}")
        job_data = json.loads(body_str)

        job_id = job_data["job_id"]
        highlights = job_data["highlights"]
        text_segments = job_data["text_segments"]
        print(f"Process an async job in the background: {job_id}, {text_segments}")

        # Update job status
        def update_job_status(status, progress=None, result=None, error=None):
            job_update = {
                "job_id": job_id,
                "status": status,
                "updated_at": context.aws_request_id if context else None,
            }
            if progress:
                job_update["progress"] = progress
            if result:
                job_update["result"] = result
            if error:
                job_update["error"] = error

            job_key = f"jobs/{job_id}.json"
            s3.put_object(
                Bucket=bucketName,
                Key=job_key,
                Body=json.dumps(job_update),
                ContentType="application/json",
            )

        # Process the job using existing logic
        update_job_status("processing", "Generating audio...")
        convert_text_to_speech(text_segments)

        update_job_status("processing", "Uploading audio...")
        upload_file_to_s3(job_id, highlights)

        # Mark job as completed
        update_job_status("completed", "Generating audio completed successfully.")

        return {
            "statusCode": 200,
            "body": {
                "job_id": job_id,
                "status": "completed",
            },
        }
    except Exception as exc:
        # Mark job as failed
        try:
            update_job_status("failed", error=str(exc))
        except:
            pass
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}


def lambda_handler(event, context):
    # Handle preflight from browsers
    if isinstance(event, dict) and event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}

    # If client wants to poll job status, handle early and return job JSON
    if event.get("action") == "job_status":
        job_id = event.get("job_id")
        if not job_id:
            return _proxy_response(400, {"error": "missing job_id"})
        try:
            job_key = f"jobs/{job_id}.json"
            result = s3.get_object(Bucket=bucketName, Key=job_key)
            job_data = json.loads(result["Body"].read())
            return {"statusCode": 200, "body": job_data}
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return _proxy_response(
                    404, {"error": "job not found", "job_id": job_id}
                )
            return _proxy_response(
                500, {"error": f"failed to get job status: {str(e)}"}
            )

    # Handle async job processing (background invocation)
    if event.get("action") == "process_job":
        return _process_async_job(event, context)

    # Check if async processing is requested
    async_mode = event.get("async", False)
    highlights = event.get("highlights", [])
    for item in highlights:
        if not item.get("text"):
            print(f"Invalid text: {item}")
            return _proxy_response(400, {"error": f"Invalid text: {item}"})

    text_segments = list(map(lambda item: item.get("text"), highlights))
    if not text_segments:
        print("No text is found.")
        return _proxy_response(400, {"error": "No text is found."})

    job_id = str(uuid.uuid4())

    # If async mode requested, start background job and return immediately
    if async_mode:
        # Create initial job record
        job_data = {
            "job_id": job_id,
            "status": "processing",
            "created_at": context.aws_request_id if context else None,
            "progress": "Starting to convert text to speech...",
        }

        # Save job status to S3
        try:
            job_key = f"jobs/{job_id}.json"
            s3.put_object(
                Bucket=bucketName,
                Key=job_key,
                Body=json.dumps(job_data),
                ContentType="application/json",
            )

            # Invoke another Lambda asynchronously to process the job
            lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
            async_payload = {
                "job_id": job_id,
                "highlights": highlights,
                "text_segments": text_segments,
            }

            lambda_client.invoke(
                FunctionName=context.function_name if context else "AdienElevenLabsPOC",
                InvocationType="Event",  # Async
                Payload=json.dumps(
                    {"action": "process_job", "body": json.dumps(async_payload)}
                ),
            )

            return {
                "statusCode": 202,
                "body": {
                    "job_id": job_id,
                    "status": "processing",
                    "message": 'Job started. Use /crawl with {"action":"job_status","job_id":"'
                    + job_id
                    + '"} to check progress.',
                },
            }

        except Exception as e:
            print(f"Failed to start async job: {str(e)}")
            return _proxy_response(
                500, {"error": f"Failed to start async job: {str(e)}"}
            )
    else:
        try:
            convert_text_to_speech(text_segments)
            upload_file_to_s3(job_id, highlights)
            print(f"Finish converting text to speech.")
            return {
                "statusCode": 200,
                "body": {
                    "id": job_id,
                },
            }
        except Exception as e:
            return _proxy_response(
                500, {"error": f"Sorry, something went wrong. {str(e)}"}
            )
