# CreativeOps Agent

Multi-agent orchestrator for creative content generation workflows. Built as a backend system for a mobile app that generates images and videos using AI.

## Architecture

The system uses multiple specialized agents that coordinate through code-level orchestration:

- **Image Agent** - Enhances creative briefs into detailed prompts using gpt-4o-mini
- **QA Agent** - Analyzes generated images using gpt-4o-mini vision capabilities
- **Orchestrator Agent** - Coordinates the pipeline (defined for MCP handoff support)

### Workflow A - Image Generation Pipeline

1. User submits a creative brief
2. Image Agent enhances the prompt with style, lighting, composition details
3. Enhanced prompt is sent to self-hosted FLUX.1-schnell model on Modal
4. QA Agent reviews the output image and scores it (1-10)
5. If score < 7.0, regenerates with QA feedback (max 2 retries)
6. Returns approved image with metadata

### Workflow B - Video Generation Pipeline

Planned - Image-to-video pipeline using Wan2.1 on Modal.

## Tech Stack

- **Agent Framework**: OpenAI Agents SDK - chosen for native MCP support and clean multi-agent API
- **LLM**: OpenAI gpt-4o-mini - cost effective, supports vision for QA
- **Image Generation**: FLUX.1-schnell on Modal (self-hosted, serverless GPU)
- **Observability**: Langfuse with @observe decorator
- **API**: FastAPI
- **MCP**: FastMCP server exposing generation and analysis tools
- **Demo UI**: Gradio

## Why OpenAI Agents SDK?

I considered LangGraph, CrewAI, and Google ADK. I chose OpenAI Agents SDK because:

- Built-in MCP support without extra configuration
- Clean handoff mechanism between agents
- Minimal boilerplate compared to LangGraph
- Well documented and actively maintained

Trade-off: tightly coupled to OpenAI as LLM provider. For this project that was acceptable since we use gpt-4o-mini anyway.

## Setup
```bash
git clone https://github.com/YOUR_USERNAME/creativeops-agent.git
cd creativeops-agent
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys:
```
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Running

API server:
```bash
uvicorn main:app --reload
```

Demo UI:
```bash
cd ui
python app.py
```

Test workflow:
```bash
python test_workflow_a.py
```

## API Endpoints

- `GET /health` - Health check
- `POST /workflow/image` - Trigger image generation workflow
```json
{
  "creative_brief": "A cyberpunk portrait of a samurai in a neon-lit Tokyo alley",
  "aspect_ratio": "1:1",
  "seed": 42
}
```

## MCP Server

The MCP server exposes two tools:

- `generate_image` - Calls FLUX model on Modal
- `analyze_image` - QA analysis using gpt-4o-mini vision

Run with:
```bash
python mcp_server/media_server.py
```

## Observability

Langfuse traces every workflow run. Each trace includes prompt enhancement, image generation, and QA analysis spans.

Dashboard: https://cloud.langfuse.com

## Cold Start Handling

FLUX model on Modal uses `scaledown_window=300` to keep the container warm for 5 minutes after the last request. First request after cold start takes ~45s (model loading), subsequent requests take ~5-6s.

## Project Structure
```
creativeops-agent/
├── my_agents/           # Agent definitions
├── tools/               # Tool functions (image gen, QA)
├── mcp_server/          # MCP server with FastMCP
├── modal_serving/       # Modal GPU model code
├── workflows/           # Workflow orchestration
├── config/              # Settings and constants
├── ui/                  # Gradio demo interface
├── tests/               # Test suite
├── main.py              # FastAPI application
├── Dockerfile           # Container for deployment
└── .github/workflows/   # CI/CD pipelines
```