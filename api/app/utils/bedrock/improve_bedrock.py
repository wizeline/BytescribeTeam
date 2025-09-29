import boto3
import json
import os

region = os.getenv("BEDROCK_REGION", "us-east-1")
runtime = boto3.client("bedrock-runtime", region_name=region)
sample_url = "https://wizeline.atlassian.net/wiki/spaces/VS/pages/5029921190/Article+to+Video"
sample_images = [
    {
        "title": "Application diagram",
        "caption": "How application works",
        "tags": ["application", "diagram"],
        "s3_url": "s3://bytescribeteam/application_diagram.png"
    },
    {
        "title": "Stepfunction workflow",
        "caption": "Stepfunction for all tasks",
        "tags": ["stepfunction"],
        "s3_url": "s3://bytescribeteam/stepfuction-workflow.png"
    }
]
sample_article = "1. Architecture Amplify - live news segment api Step function - MREReplayGenerationStateMachine ArticleToVideo lambda VideoCaptionEventHandler lambda DynamoDB S3 2. Reels Flow This is a Step Function with a name that starts with 'MREReplayGenerationStateMachine' Example a Flow: Source code refs /source/backend/replay folder article_replay_handle.py under /samples/source/article-to-video/infrastructure folder 3. ImageServices 1.  GettyImages Docs: https://docs.google.com/document/d/1ZMJmbt-ghBJBN03B4Rt_1Y6yI8ZU7oo5vI17isyJF7Y/edit?usp=sharing 2. Blue Larkspur SDK Docs: https://docs.google.com/document/d/1nyOxgbeBWM65-0YKHzke_zseyQXFllU-f8HHG68-xqA/edit?usp=sharing 3. Bedrock Agent + KB Docs: https://docs.google.com/document/d/154SR-_RLG9Kya-9LWt1M5BiasRY9bvnYZp5iYnb1kus/edit?usp=sharing 4. Caption Requirement: Caption with style \u201cword highlight by speaker\u201d Libs: moviepy ffmpeg 16:9 resolution flows During a2v reels processing then create 16:9 video, upload some files to S3 with path <s3_bucket>/mp4replay/<replay_id>. The files are: Original 16:9 video with no caption Caption file: polly_caption_<uuid>.json Invoke VideoCaption lambda with 1 json payload expected to add caption to video and upload file to 16:9 resolution folder. lambda will download file video and caption from s3 to local From json caption file will split to segments include start, end time and text base on MAX_WORDS_IN_LINE configuration Base on caption segments => reduce to caption track items what includes font styles, position, and highlight colors to add to video Use moviepy + caption track items to put text to video Upload result to s3 with output from payload Payload sample: {'State': 'ADD_CAPTION_TO_VIDEO', 'Event': {'Name': 'a2v Hackmans', 'Program': 'News'},\n                               'Payload': {\n                                   'Input': {\n                                        'Media': {\n                                           'S3Bucket': 'aws-mre-shared-resources-mremediaoutputbucket47893-jgua8ojywbzj',\n                                           'S3Key': 'mp4replay/9da83fa8-f1cf-46c5-a920-91331f35162a',\n                                           'ClipName': 'News_a2v Blue Origin_9da83fa8-f1cf-46c5-a920-91331f35162a.mp4'},\n                                        'Caption': {\n                                           'S3Bucket': 'aws-mre-shared-resources-mremediaoutputbucket47893-jgua8ojywbzj',\n                                           'S3Key': 'mp4replay/9da83fa8-f1cf-46c5-a920-91331f35162a',\n                                           'FileName': 'polly_caption_News_a2v Blue Origin_9da83fa8-f1cf-46c5-a920-91331f35162a.json',\n                                        'Source':'a2v'}\n                                    },\n                                   'Output': {\n                                       'Media':{\n                                    'S3Bucket': 'aws-mre-shared-resources-mremediaoutputbucket47893-jgua8ojywbzj',\n                                       'S3Key': 'mp4replay/9da83fa8-f1cf-46c5-a920-91331f35162a/16:9',\n                                       'ClipName': 'News_a2v Blue Origin_9da83fa8-f1cf-46c5-a920-91331f35162a.mp4'\n                                       }\n                                   },\n                                   'Configuration': {\n                                       'MAX_WORDS_IN_LINE': 8\n                                   }\n                               }} 9:16 resolution flows: After a2v reel to create 16:9 video done then will call 9:16 batch job to create video 9:16 format After 9:16 video created then will follows similar above steps  to add 16:9 to captions Source code refs video_helper.py under /samples/source/article-to-video/infrastructure folder VideoCaptionEventHandler under /samples/source/wl-function-samples/Functions 5. Hot deploy in developing process 1. Setup env: export AWS_DEFAULT_REGION=\nexport AWS_DEFAULT_REGION=\nexport AWS_PROFILE= 2. Script deploy Live News Segment API # cd to /samples/source/live-news-segmenter/api/infrastructure\n# run command\ncdk deploy VideoCaptionEventHandler # cd to /samples/deployment\n# run script\n./build-and-deploy.sh --app wl-function-samples ArticleToVideo # cd to /samples/source/article-to-video/infrastructure\n# run command\ncdk deploy Reels # cd to /source/backend/replay/infrastructure\n# run command\ncdk deploy"


def summarize_and_select_images(article_text: str, images_json: list[dict]):
    prompt = f"""You are given a long article and a list of candidate images (each includes title, caption/tags, and an S3 URL).
        Tasks:
        1) Produce 3 main bullet points summarizing the core ideas of the article (≤60 words each, no overlap).
        2) For each bullet point, select at most three best-matching images from the provided list.
        3) If there is no any suitable images, return empty images and not invent images.
        4) Return a valid JSON object with this schema:
        {{
        "bullets": [
            {{
            "text": "<<=60 words>>",
            "reason": "<<why this image fits, 1 sentence>>",
            "image_url": "<<a list of suitable provided images in s3 URLs>>"
            }}
        ]
        }}

        Important rules:
        - Base your image choice ONLY on the provided image titles/captions/tags (no external fetching).
        - Output JSON only. No markdown. No explanations outside JSON.

        ARTICLE:
        <<<
        {article_text}
        >>>

        IMAGES:
        <<<
        {json.dumps(images_json, ensure_ascii=False)}
        >>>
    """

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    res = runtime.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )
    out = json.loads(res["body"].read())
    print(json.dumps(out, indent=4))
    text = json.loads(out["content"][0].get("text", {})).get("bullets", [])
    print("\n\n--------------------------------")
    print(json.dumps(text, indent=4))
    return text


summarize_and_select_images(sample_article, sample_images)
