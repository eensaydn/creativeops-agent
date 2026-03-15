# CreativeOps Agent

Multi-agent system that generates images and videos from creative briefs.

## Demo Video

[Loom Video - Architecture walkthrough and live demo](LOOM_LINK_HERE)

## Live URLs

- API: https://creativeops-agent-983099118800.us-central1.run.app
- Demo UI: https://creativeops-agent-983099118800.us-central1.run.app/ui
- Swagger Docs: https://creativeops-agent-983099118800.us-central1.run.app/docs
- Observability: https://cloud.langfuse.com (credentials shared separately)

## How it works

There are two workflows:

Workflow A (Image Generation): User gives a text brief like "cyberpunk samurai in Tokyo". The Image Agent enhances the prompt, FLUX model generates the image on Modal, QA Agent checks quality with vision. If score is below 7/10 it retries with feedback, up to 2 times. Returns the image with metadata, QA score, and cost breakdown.

Workflow B (Image-to-Video): User uploads an image and gives a motion prompt like "slow camera pan right". The Video Agent enhances the motion prompt, Wan2.1-I2V-14B model generates a video on Modal. Returns the video with metadata and cost breakdown.

## Architecture overview

The system uses code-level orchestration instead of full agent handoffs. I tried handoffs first but base64 image data is millions of characters and doesn't fit in the LLM context window. So the LLM only handles reasoning (like prompt enhancement and QA scoring) and the data flow happens in code. This is actually the right pattern for production too - you don't want to pass huge binary data through an LLM.

Agents:
- Image Agent - takes a brief and makes it into a better prompt for FLUX
- Video Agent - takes a motion prompt and enhances it for Wan2.1
- QA Agent - looks at generated images using gpt-4o-mini vision and scores them
- Orchestrator Agent - defined with handoffs for MCP support

Tools:
- image_tool.py - calls FLUX endpoint on Modal
- qa_tool.py - calls gpt-4o-mini vision for quality analysis
- video_tool.py - calls Wan2.1 endpoint on Modal

MCP Server:
- media_server.py exposes generate_image and analyze_image as MCP tools using FastMCP

Observability:
- Langfuse with @observe decorator on both workflows
- Cost tracking per workflow (LLM token costs + GPU inference costs)

## Framework choice

I picked OpenAI Agents SDK. Here's why and what else I considered:

OpenAI Agents SDK - what I went with. It has built-in MCP support which was a requirement. The API is clean, you define an Agent with instructions and tools and it just works. Multi-agent handoffs are built in. Less boilerplate than LangGraph.

LangGraph - I looked at this. It's powerful and flexible but requires more setup. You need to define state schemas, graph nodes, edges etc. For this project it felt like overkill. Good for complex stateful workflows though.

The trade-off with OpenAI Agents SDK is that you're tied to OpenAI as LLM provider. But since I'm using gpt-4o-mini anyway (cheap and has vision support) this wasn't a problem. If I needed to switch providers later I'd probably move to LangGraph.

## Why gpt-4o-mini for everything?

I originally planned to use Gemini for QA since it's free. But Google cut their free tier limits in late 2025 and I kept hitting 429 errors. Switched to gpt-4o-mini with detail:low for vision analysis. It's cheap (about $0.001 per QA call) and works well.

## Self-hosted models

Image: FLUX.1-schnell on Modal (L40S GPU)
- scaledown_window=300 for cold start management
- Cold start takes ~45s, then ~5s per image
- Model cached in Modal Volume

Video: Wan2.1-I2V-14B on Modal (A100-80GB GPU)
- enable_model_cpu_offload() because 14B params needs careful memory management
- Had to use A100-80GB, A100-40GB gave OOM errors
- output_type="pil" needed because default numpy output caused issues
- follow_redirects=True in httpx client because Modal returns 303 for long-running requests
- Cold start takes ~2min, inference ~100s

## Cost tracking

Each workflow returns a cost_breakdown with llm_cost, gpu_cost, and total_cost. GPU costs are calculated from actual inference latency times the per-second rate of the GPU used (L40S: $0.000542/s, A100-80GB: $0.000694/s).

## Setup
```
git clone https://github.com/eensaydn/creativeops-agent.git
cd creativeops-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy .env.example to .env and fill in your keys:
```
OPENAI_API_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## How to run locally

Start the API + Gradio UI:
```
uvicorn main:app --reload
```

Then open:
- http://127.0.0.1:8000/ui for the Gradio demo
- http://127.0.0.1:8000/docs for Swagger API docs

## How to run workflows

From the UI: go to /ui, pick a tab (Image or Video), fill in the fields, click generate.

From the API:
```
curl -X POST https://creativeops-agent-983099118800.us-central1.run.app/workflow/image \
  -H "Content-Type: application/json" \
  -d '{"creative_brief": "a sunset over mountains"}'
```

From code:
```
python test_workflow_a.py
python test_video.py
```

## API endpoints

GET /health - health check
POST /workflow/image - image generation (takes creative_brief, aspect_ratio, seed)
POST /workflow/video - video generation (takes image_base64, motion_prompt, num_frames)

## Deployment

Deployed on GCP Cloud Run. Dockerfile included. CI/CD with GitHub Actions (lint, test, deploy).

## Project structure
```
my_agents/        - agent definitions (image, video, qa, orchestrator)
tools/            - tool functions (image, video, qa)
mcp_server/       - MCP server with FastMCP
modal_serving/    - GPU model code for Modal
workflows/        - workflow orchestration (a and b)
config/           - settings
ui/               - standalone Gradio app (for local dev)
tests/            - basic tests
main.py           - FastAPI + mounted Gradio
Dockerfile        - for GCP Cloud Run
.github/workflows - CI/CD (lint, test, deploy)
```