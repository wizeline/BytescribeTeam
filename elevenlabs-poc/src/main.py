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

def lambda_handler(text, fileName="output.mp3"):
    print(f"Start converting text: {text}")
    try:
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        print(f"Audio generated, saving to {fileName}.mp3...")
        save(audio, fileName)
        print(f"File {fileName} saved successful.")
    except Exception as e:
        print(e)
        print(f'Error requesting ElevenLabs convert {text} to speech.')
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert text to speech using ElevenLabs API.")
    parser.add_argument("text", type=str, help="Text to convert to speech")
    args = parser.parse_args()
    lambda_handler(args.text)