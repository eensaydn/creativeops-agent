# Further Improvements

How I'd evolve this system for production scale.

## MCP Integration & Asset Storage Layer

Right now the MCP server works - it exposes 3 tools (generate_image, generate_video, analyze_image) and any MCP client can connect and call them. I tested this with a client script that triggers tools via MCP protocol and it works fine.

But the workflows don't use MCP internally. They call tool functions directly via Python imports. The reason is practical: a single generated image is ~2 million characters of base64 data. If an agent calls a tool via MCP and gets that back, it lands in the LLM's context window. gpt-4o-mini has a 128K token limit, 2 million characters is roughly 500K tokens. It simply doesn't fit.

The right fix is an asset storage layer. Instead of passing raw base64 between agents, each tool saves the generated asset to a storage service and returns just an ID or URL. The flow would look like:

1. Agent calls generate_image via MCP
2. The tool generates the image, uploads it to S3 or Google Cloud Storage, returns `{"asset_id": "img_abc123", "model_used": "FLUX.1-schnell"}`
3. Agent passes that asset_id to the QA tool via MCP
4. QA tool fetches the image from storage using the asset_id, analyzes it, returns the score

Now agents only pass small strings (asset IDs, scores, feedback) through the LLM context. The heavy binary data lives in storage and never touches the LLM.

For the storage layer I'd use Redis for short-lived assets during workflow execution (fast reads, auto-expiry after 1 hour) and Google Cloud Storage for final approved assets that need to persist. This also solves the data persistence problem - right now everything is stateless, once a workflow returns its result the image is gone. With GCS the assets stick around and can be served to the mobile app via a CDN.

This change would make the full agent-to-agent MCP pipeline work: Orchestrator Agent delegates to Image Agent via MCP handoff, Image Agent calls generate_image MCP tool, gets back an asset_id, passes it to QA Agent via MCP handoff, QA Agent calls analyze_image MCP tool with the asset_id. All through MCP, no base64 in context.

## Moving from API Models to Fine-tuned Open Source Models 

https://research.nvidia.com/labs/lpr/slm-agents/ (I'm working on multi-agent systems for my master)

Right now the system uses OpenAI's gpt-4o-mini for everything - prompt enhancement, QA scoring, vision analysis. It works and it's cheap, but we're still paying per token and we depend on an external API.

There's a recent NVIDIA research paper ("Small Language Models are the Future of Agentic AI", 2025) that argues most tasks in agentic systems are repetitive and narrow enough that small open source models (under 10B parameters) can handle them just as well as big models. Their point is simple: agents don't need a genius generalist, they need a reliable specialist.

This fits our system well. Our agents do the same few things over and over - enhance a prompt, score an image, check quality. These are exactly the kind of narrow, repetitive tasks where a fine-tuned 7-8B model can match gpt-4o-mini. Models like Phi-3 (7B), SmolLM2 (1.7B), or xLAM-2 (8B) already show competitive performance on tool calling and instruction following compared to much larger models.

The path would be: collect prompt-response pairs from our production traffic (the Data Flywheel above), fine-tune something like Llama 3 8B or Phi-3 with LoRA, self-host it on the same Modal infrastructure we already use for image/video models. No more per-token API costs, no external dependency, and we control the model completely.

This isn't something I'd do on day one - the OpenAI API is fine for getting started. But at scale with millions of users, switching the agent backbone from paid API to self-hosted fine-tuned SLM would cut LLM costs significantly.

## FinOps & Cost Optimization

Right now cost tracking is basic - GPU cost from inference latency and LLM cost from real token usage. Works for a demo but not at scale.

**Cloud vs on-prem decision:** The first big question at scale is whether serverless GPU is even worth it. Right now a single video generation costs ~$0.10 on Modal's A100-80GB. At 1000 videos/day that's $3,000/month. A dedicated H200 lease runs roughly $1,500-2,200/month and handles way more throughput with no cold starts. The break-even depends on utilization - if GPUs sit idle most of the day, serverless wins. If utilization is consistently above 40-50%, dedicated hardware is cheaper. I'd track daily request volume and GPU utilization, and alert when it crosses that threshold.

**Budget caps:** Each workflow run should have a budget limit (e.g. max $0.50 for image, max $1.00 for video). If a retry is about to blow the budget, return the best result so far instead of spending more. Daily spend alerts via Slack when we cross $50, $100, $500.

**Cost-based routing:** Simple prompts → cheap FLUX-schnell on L40S. Complex prompts → FLUX-dev on A100. If all self-hosted models are down → fall back to managed APIs like fal.ai (expensive but no cold starts). Start with simple rules, get smarter over time using QA score history.

**Dashboard:** Grafana pulling from Langfuse - cost per workflow type, average QA score, retry rate, P95 latency, cold start frequency.

## Content Moderation

Right now the system accepts every prompt. In a consumer app that's a problem - people will try to generate NSFW content, violence, copyrighted characters, etc. and you don't want to waste GPU money on stuff you'll have to reject anyway.

The fix is a lightweight moderation layer between the API gateway and the agents. Something like OpenAI's Moderation API or Llama Guard - these are very cheap and fast. Check the prompt before it ever hits a GPU. If it violates the rules, reject it immediately with a clear message. This saves both money and legal headaches.

## Database Schema & Data Design

Currently everything is stateless - results go back to the caller and that's it. For production I'd use PostgreSQL (handles JSON well, battle-tested) with these tables:

- **workflow_runs** - id, type (image/video), status, brief, user_id, timestamps, total_time, metadata as jsonb
- **generation_results** - id, workflow_run_id, attempt number, model used, asset URL (GCS path, not base64), params, latency
- **qa_results** - id, generation_result_id, scores (overall, adherence, quality), feedback, token usage
- **cost_records** - id, workflow_run_id, cost type (llm/gpu/storage), amount, provider, token count

For assets (images, videos) - store in Google Cloud Storage with a CDN in front. Hot storage for recent stuff, cold storage for older assets. Signed URLs for secure access. Cleanup job to delete unclaimed assets after 7 days.

## Data Flywheel

The QA scores and feedback sitting in the database shouldn't just be metrics. High QA scoring prompts and their generated images are basically free training data. Over time I'd collect these into a dataset and fine-tune a smaller, cheaper model (like Llama 3 8B) to do prompt enhancement instead of gpt-4o-mini. The system's own output makes the system smarter and cheaper over time - that's the flywheel.

## Service Architecture & Scalability

The current system is a monolith - FastAPI handles everything in one process. For production:

**Async job processing:** This is the #1 priority. Video generation takes 2-3 minutes and blocks the HTTP request. Should return a job_id immediately and let the client poll or use webhooks.

**Real-time status updates:** Once we have the job queue, users shouldn't stare at a blank screen for 3 minutes. I'd add WebSockets or Server-Sent Events to push status updates in real time: "Request queued → Prompt enhancing → Model loading → Generating video → QA checking". When it's done and the user has left the app, send a push notification.

**Rate limiting:** Per-user limits (10 images/min, 3 videos/min), daily budget cap ($5/day for free tier), and a circuit breaker that backs off if the GPU provider error rate goes above 30%.

**Failover:** Each inference provider gets a health score based on recent errors and latency. Primary: Modal → Fallback: RunPod → Last resort: managed API. If all self-hosted options are down, managed APIs keep the service alive even if they're more expensive.

**Caching:** Redis cache for repeated prompts (same brief → same enhanced prompt, skip the LLM call). Keep at least 1 GPU warm during peak hours with Modal's min_containers setting.