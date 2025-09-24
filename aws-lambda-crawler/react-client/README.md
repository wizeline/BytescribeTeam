# React Client for AWS Lambda Crawler

A React-based web client for testing the AWS Lambda Crawler with AI-powered summarization capabilities using AWS Bedrock.

## Features

- **Parse HTML**: Extract and parse content from web pages
- **Create Document (Index)**: Process content into structured document format with chunks
- **Summarize Content**: Generate AI-powered summaries using AWS Bedrock models

### Summarization Features

- **Multiple summary lengths**: Short (1-2 sentences), Medium (1 paragraph), Long (2-3 paragraphs)
- **Focus areas**: Optional focus on specific aspects like "technical details", "key findings", or "action items"
- **Multiple AI models**: Support for various AWS Bedrock models including:
  - Claude 3 Haiku (Fast & Cost-effective)
  - Claude 3 Sonnet (Balanced performance)
  - Claude 3 Opus (Highest quality)
  - Amazon Titan models
  - AI21 Labs models

## Prerequisites

- Node.js (16+ recommended)
- npm or yarn

## Setup

1. Navigate to the react-client directory:

```bash
cd react-client
```

1. Create a `.env` file with your API URL:

```env
VITE_API_URL="https://{api-id}.execute-api.{region}.amazonaws.com/Prod/crawl"
```

1. Install dependencies and start the development server:

```bash
npm install
npm run dev
```

1. Open <http://localhost:5173> in your browser to access the client.

## Usage

1. Enter a URL you want to process
2. Choose your action:
   - **Parse HTML**: Basic content extraction
   - **Create Document (Index)**: Structured document processing
   - **Summarize Content**: AI-powered summarization
3. For summarization, configure:
   - Summary length (short/medium/long)
   - Focus area (optional)
   - AI model selection
4. Click the action button to process

## Configuration

- The app reads `VITE_API_URL` at build/dev time from `.env` file
- Make sure your deployed API has CORS configured to allow the client origin
- For local development, ensure CORS allows `http://localhost:5173`

## Notes

- Summary quality and speed vary by model selection
- Claude models generally provide better results but may have higher costs
- Focus areas help tailor summaries to specific needs
- All processing is done server-side using AWS Bedrock
