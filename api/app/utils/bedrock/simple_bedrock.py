import boto3
import json

runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

# prompt = "Summarize the benefits of Amazon Bedrock in 3 bullet points."
_DEFAULT_PROMPT = """
    Summarize the following text into exactly 3 main bullet points:
    - Each bullet point must be no longer than 50 words.
    - Focus only on the core ideas, avoid minor details or repetition.
    - Return the output as plain text bullets.

    Text:\n
"""

content_page = """
    This document provides a comprehensive technical overview of the Wize Media Suite, a robust platform designed for efficient media content management. We will explore the system's core capabilities, from the initial ingestion of video assets to the sophisticated generation and strategic publication of refined content. Our discussion emphasizes the suite's AI-driven functionalities and its extensive customization options. Meeting Core Requirements and Gaining Access For optimal performance, meeting specific video prerequisites is essential. Videos must adhere to the MP4 format, maintaining a maximum file size of 4 GB, although the system can accommodate up to 13 GB with a stable, high-throughput internet connection. Furthermore, video durations should not exceed 4 hours, and a minimum duration of 4 minutes is required for the tool to yield meaningful analytical output. File naming conventions also demand attention: names should exclusively contain letters, numbers, dashes, or underscores, strictly avoiding spaces or special symbols. To access Wize Media Suite , users are required to log in, providing their credentials on the designated URL. Streamlining Event and Media Content Management Wize Media Suite incorporates a tailored version of the AWS Media Replay Engine (MRE), specifically optimized for seamless event creation and administration. This adaptation empowers both administrators and editors to create new events directly from MRE, configuring crucial details such as the program type (e.g., sports, news), the unique event name, the appropriate processing profile (e.g., chapterization, news segmentation), and the relevant content group. Users can also define the timecode source, choosing between NOT_EMBEDDED for non-live events or UTC_BASED or ZERO_BASED for live broadcasts, and establish the maximum duration allocated for segmentation processing. Additionally, the platform facilitates the customization of prompts through the direct editing of templates within DynamoDB, allowing users to precisely tailor instructions for content generation. Navigating Event Exploration and Detailed Insights Upon successful login, the event listing page serves as the primary interface, where users can readily view all uploaded events. This page provides a visual preview of each event, its assigned name, the precise creation date and time, the associated program, the relevant content group, and its current processing status (either complete or in progress). Furthermore, users can explore the detailed aspects of a selected event , gaining access to its linked video reels, granular segmentations, accurate timestamps, and concise descriptive summaries for each segment. This comprehensive view enables editors and producers to swiftly assess key moments within the content analyzed by Wize Media Suite, offering the flexibility to view segments chronologically by timeline or to group them thematically. Mastering Segment Manipulation and Intelligent Search Wize Media Suite furnishes robust tools for both manipulating and intelligently searching specific content segments. The favorite segments feature allows users to easily select and organize important segments from the event list, which are then conveniently displayed under the \"My Playlist\" tab. From this section, users can either generate customized reels based on these favored segments or export them as an EDL file. The powerful capability to search segments and create reels , driven by Wize Media Suite's advanced AI, simplifies the process of locating specific insights within an event. Search results include a concise description and a list of pertinent clips, from which users can either preview individual segments or generate new reels with varying resolutions and transition effects. For a more in-depth review, the open clip segment option enables users to view individual clips, perform edits, export EDL files, or even publish them directly. This detailed view provides essential metadata such as start and end times, identified speakers, sentiment analysis, recognized celebrities, clip transcriptions, and image summaries. Facilitating Final Content Generation and Seamless Publishing The platform is meticulously engineered for the efficient creation and streamlined distribution of final content. Once generated, users can view reels directly within the Event Details page, selecting their preferred resolution from the available options. Reels are meticulously optimized for the chosen resolution, ensuring consistently high visual quality. Beyond mere viewing, the platform empowers users to download generated reels or publish them directly to various social media platforms , thereby facilitating effortless cross-platform distribution. For live events, Wize Media Suite offers the critical option to set up UTC timecode for live processing . This involves precisely adjusting the MediaLive channel's configuration to utilize a SYSTEMCLOCK timecode and carefully selecting UTC_BASED as the embedded timecode source during event creation, ensuring the accurate synchronization of live segments. Infrastructure Diagram Please add here the infrastructure diagram File Structure Please add here the file structure
"""

# body = json.dumps({
#     "inputText": _DEFAULT_PROMPT + content_page,
#     "textGenerationConfig": {
#         "maxTokenCount": 8192,
#         "temperature": 0.7
#     }
# })
# print(body)
body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
        {"role": "user", "content": _DEFAULT_PROMPT + content_page}
    ]
}

response = runtime.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
    contentType="application/json",
    accept="application/json",
    body=json.dumps(body),
)

output = json.loads(response["body"].read())
print(output)
print(output["content"][0]["text"])

# resp = runtime.invoke_model(
#     modelId="amazon.titan-text-express-v1",  # modelId từ list_foundation_models
#     body=body,
#     contentType="application/json",
#     accept="application/json"
# )

# output = json.loads(resp["body"].read())
# print(json.dumps(output, indent=4))
# for idx, result in enumerate(output.get("results", [])):
#     print(f"---> Result {idx}:", result.get("outputText", ""))
