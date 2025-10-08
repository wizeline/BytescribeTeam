<img width="265" height="250" alt="image" src="https://github.com/user-attachments/assets/95e00215-93a7-4557-85f7-25aac59292db" />


<h1>Team Bytescribe - Page2Play</h1>


<h2>Main Objective</h2>

The primary goal of the Page2Play solution is to combat information overload by transforming long, dense text on Confluence pages into concise, engaging video summaries. We aim to save users time, boost productivity, and make knowledge more accessible for individuals and teams.

<h2>Specific Objectives</h2>

Our Minimum Viable Product (MVP) is designed to deliver a core value proposition with a focused set of features. The MVP must be able to:
* **Ingest Confluence Page Content**: Take a Confluence page URL and automatically extract its HTML content, filtering out irrelevant data like ads and navigation menus.
* **Generate Key Highlights**: Use an AI model to intelligently identify and extract the most important information from the page content.  
* **Create Video from Highlights**: Generate simple, engaging videos using the extracted highlights.  
* **Incorporate Text-to-Speech**: Convert the textual highlights into a natural-sounding audio narration for the videos.
* **Combine and Finalize**: Stitch together the audio, visual elements (static images), and captions into cohesive video files.
* **Provide a Playable Output**: The user should be able to play the final videos summary easily.

<h2>Tech Stacks</h2>

The chosen tech stack is based on a serverless architecture, prioritizing scalability and development velocity.
* **Frontend**: The user interface is built using React and Next.js.
* **Backend**: All backend logic is implemented in Python and deployed on AWS Lambda.
* **AI/NLP**: AWS Bedrock is used for the core AI logic to generate highlights from the source text.
* **Database**: Amazon DynamoDB stores the results and metadata of the video generation process.
* **Video & Audio Generation**: We use open-source libraries like moviepy (https://pypi.org/project/moviepy/) for combining video and audio, and integrate with services ElevenLabs (https://elevenlabs.io/) for text-to-speech functionality.

<h2>Scalability from MVP to Production</h2>

The current serverless architecture provides a strong foundation for future growth. Our plan to scale includes:
* **Horizontal Scaling**: The use of Lambda functions means our solution can automatically handle a high volume of requests without significant changes to the code.
* **Robust Content Ingestion**: We will expand our crawling capabilities to handle more complex Confluence page layouts, tables, and embedded media.
* **Enhanced AI Models**: We will fine-tune our AI models for better summarization accuracy and add support for multi-language summarization.
* **Automated Image Selection**: We will implement an AI Agent to automatically select contextually relevant images from the source content to enrich the generated video summaries, reducing manual effort and improving the quality of the output.
* **Video Customization**: We will introduce more customization options for users, such as choosing different voices, video templates, and adding their own images or branding.
* **Automated Presentation Generation**: We will expand our solution to generate full video presentations with a structured flow and visual elements, empowering users to transform documentation into professional, ready-to-use slide decks.
* **Confluence Add-on**: The long-term plan is to develop an official Confluence add-on, providing a seamless, one-click experience directly within the platform.

<h2>Architecture Overview</h2>

<img width="1024" height="683" alt="Page2Play_Architecture" src="https://github.com/user-attachments/assets/7af57402-17b3-4025-a667-f02a4d176418" />

<h2>Architecture Components</h2>

Our solution, Page2Play, is built on a modern, serverless architecture that is designed for scalability and cost-efficiency. This approach allows us to pay only for the compute time we use, automatically scale with demand, and focus on our core logic rather than infrastructure management. The key components of our architecture are all part of the Amazon Web Services (AWS) ecosystem.

<h4>Frontend (React/Next.js)</h4>
We're using React for building a dynamic user interface and Next.js to handle server-side rendering and routing. This provides a fast, responsive user experience for a web-based application.

<h4>AWS Lambda</h4>
We're using two distinct Lambda functions in our MVP, both written in Python, to manage the core logic:
Ingestion & Highlighting Lambda: This function is triggered by the user's request. It's responsible for fetching the Confluence page content and then interacting with AWS Bedrock to get the key highlights.
Video Generation Lambda: This function is triggered by an event stream from our database. It handles the computationally intensive task of turning the highlights into a video, including text-to-speech and combining the final file.

<h4>AWS Bedrock</h4>
We will leverage Bedrock to intelligently analyze the dense Confluence page text and extract the most important information, which will then form the basis of our video summary. This allows us to use a powerful, pre-trained model for content summarization without the need to build our own from scratch.

<h4>Amazon DynamoDB</h4>
We will use DynamoDB to store the highlights and metadata extracted from the Confluence page. The key benefit of DynamoDB for us is its ability to scale to any size and its event-driven capabilities, which allow us to trigger the Video Generation Lambda as soon as new data is saved.

<h4>Amazon S3</h4>
We will use an S3 bucket as a central repository to store our final video files. S3 is highly reliable and is the perfect service for delivering video content to our users via a URL.

<h2>Business Model</h2>

Initially, we will offer a freemium model. A limited number of free video generations per month to attract users, with a tiered subscription plan for higher usage, advanced features, and team-based accounts.

<h2>Additional Information</h2>

<h4>Roadmap:</h4>
			Phase 1 (MVP): Build a functional MVP that can turn a Confluence page into a video summary.<br />
	 		Phase 2: Improve the quality and efficiency of the video output and begin to automate content enrichment.<br />
			Phase 3: Achieve widespread adoption by integrating into the user's workflow and expanding our feature set.

<h4>Pricing:</h4>
      Pricing will be based on usage, likely a "per video" cost with volume discounts. A premium tier could offer unlimited videos and advanced features.

<h4>Possible Problems:</h4>
      The main challenges will be the accuracy of the AI summarization for highly technical content, and the cost of AI model usage.<br />
	  We must also manage the performance of video generation to ensure a good user experience.
