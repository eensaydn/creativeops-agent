# CreativeOps Agent

Multi-agent orchestration system for AI-powered creative content generation. Built with OpenAI Agents SDK, self-hosted GPU models on Modal, and deployed on GCP Cloud Run.

The system receives high-level creative briefs, decomposes them into steps, coordinates between specialized agents and self-hosted models, and produces final outputs with quality control and cost tracking.

## Architecture
```
                         ┌──────────────────┐
                         │   FastAPI + UI    │
                         │   (Gradio)        │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                             │
            ┌───────▼───────┐           ┌────────▼────────┐
            │  Workflow A    │           │   Workflow B     │
            │  (Image Gen)   │           │  (Image→Video)  │
            └───────┬───────┘           └────────┬────────┘
                    │                             │
         ┌──────────┼──────────┐       ┌──────────┼──────────┐
         │          │          │       │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌──▼──┐ ┌──▼────┐ ┌──▼─────┐ ┌──▼──┐
    │ Image  │ │  FLUX   │ │ QA  │ │ Video │ │ Wan2.1 │ │ QA  │
    │ Agent  │ │ (Modal) │ │Agent│ │ Agent │ │(Modal) │ │Agent│
    │gpt-4o  │ │ L40S    │ │gpt4o│ │gpt-4o │ │A100-80 │ │gpt4o│
    └────────┘ └────────┘ └─────┘ └───────┘ └───────┘ └─────┘
                    │                             │
              ┌─────▼─────┐                 ┌─────▼─────┐
              │  Langfuse  │                │  Langfuse  │
              │  (trace +  │                │  (trace +  │
              │   costs)   │                │   costs)   │
              └───────────┘                └───────────┘
```

## Workflows

**Workflow A — Image Generation Pipeline**

1. User submits a creative brief (e.g. "cyberpunk samurai in neon-lit Tokyo")
2. Image Agent enhances the prompt with lighting, composition, style details
3. Enhanced prompt goes to self-hosted FLUX.1-schnell on Modal (L40S GPU)
4. QA Agent analyzes the generated image using gpt-4o-mini vision
5. If QA score < 7/10, regenerates with feedback (max 2 retries)
6. Returns approved image + metadata + QA score + cost breakdown

**Workflow B — Image-to-Video Pipeline**

1. User provides an image and a motion prompt (e.g. "slow camera pan right")
2. Video Agent enhances the motion prompt with camera movement details
3. Enhanced prompt + image goes to self-hosted Wan2.1-I2V-14B on Modal (A100-80GB)
4. QA Agent analyzes the output for quality and motion coherence
5. Returns video + metadata + QA score + cost breakdown

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Agent Framework | OpenAI Agents SDK | Built-in MCP support, clean API, multi-agent handoffs |
| LLM | gpt-4o-mini | Cheap, vision support for QA, good for prompt engineering |
| Image Model | FLUX.1-schnell | Fast inference, good quality, open source |
| Video Model | Wan2.1-I2V-14B | Image-to-video, open source, 14B params |
| GPU Platform | Modal | Serverless GPUs, pay-per-second, cold start management |
| API | FastAPI | Async, auto-generated docs, easy to deploy |
| Observability | Langfuse | Tracing, cost tracking, token usage logging |
| MCP | FastMCP | Exposes tools via Model Context Protocol |
| Deployment | GCP Cloud Run | Serverless, scales to zero, Dockerfile based |
| Demo UI | Gradio | Quick prototyping, mounted on FastAPI |
| CI/CD | GitHub Actions | Lint (ruff), test (pytest), deploy |

## Key Design Decisions

**Code-level orchestration over agent handoffs**

Initially tried full agent handoffs where the orchestrator delegates to image agent, then to QA agent. But base64 image data is millions of characters and blew up the LLM context window. Switched to a pattern where LLM handles reasoning (prompt enhancement, QA scoring) and code handles data flow. This is the right approach for production — binary data should never flow through an LLM.

**gpt-4o-mini for QA instead of Gemini**

Originally planned to use Google Gemini for QA (free tier). But Google cut their free tier limits significantly in late 2025, causing constant 429 rate limit errors. Switched to gpt-4o-mini with `detail: low` for vision — costs about $0.002 per QA call.

**GPU memory management for video model**

Wan2.1-I2V-14B (14 billion params) didn't fit on A100-40GB. Solutions applied:
- Upgraded to A100-80GB
- Used `enable_model_cpu_offload()` to move inactive layers to CPU RAM
- Added `output_type="pil"` because default numpy output caused frame saving errors
- Added `follow_redirects=True` in httpx because Modal returns HTTP 303 for requests >150s

## Cost Tracking

Each workflow returns a cost breakdown:
```json
{
  "cost_breakdown": {
    "llm_cost": 0.003,
    "gpu_cost": 0.0012,
    "total_cost": 0.0042
  }
}
```

GPU costs calculated from actual inference latency:
- FLUX on L40S: $0.000542/sec
- Wan2.1 on A100-80GB: $0.000694/sec

## Setup
```bash
git clone https://github.com/eensaydn/creativeops-agent.git
cd creativeops-agent
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Fill in your API keys:
```
OPENAI_API_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

For GPU models, you need a Modal account and deployed FLUX + Wan2.1 endpoints. See `modal_serving/` for deployment code.

## Running Locally
```bash
uvicorn main:app --reload
```

- Gradio UI: http://127.0.0.1:8000/ui
- Swagger Docs: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

## API
```
GET  /health           — health check
POST /workflow/image   — generate image from creative brief
POST /workflow/video   — generate video from image + motion prompt
```

Example:
```bash
curl -X POST http://127.0.0.1:8000/workflow/image \
  -H "Content-Type: application/json" \
  -d '{"creative_brief": "a sunset over mountains"}'
```

## Project Structure
```
my_agents/           — agent definitions (image, video, qa, orchestrator)
tools/               — tool functions with observability (image, video, qa)
mcp_server/          — MCP server exposing tools via FastMCP
modal_serving/       — GPU model deployment code for Modal
workflows/           — workflow orchestration logic
config/              — settings and constants
ui/                  — standalone Gradio app for local development
tests/               — tests
main.py              — FastAPI application with Gradio mounted at /ui
Dockerfile           — container for cloud deployment
.github/workflows/   — CI/CD pipelines (lint, test, deploy)
IMPROVEMENTS.md      — production scaling roadmap
```

## Sample Output

**Workflow A:**
```
Status: approved
QA Score: 8.5/10
Model: FLUX.1-schnell
Retries: 0
Total Time: 11.16s
Cost: $0.0042 (LLM: $0.003, GPU: $0.0012)
```

**Workflow B:**
```
Status: completed
Model: Wan2.1-I2V-14B-480P
Frames: 16
Latency: 152.06s
Total Time: 219.93s
Cost: $0.1065 (LLM: $0.001, GPU: $0.1055)
```
