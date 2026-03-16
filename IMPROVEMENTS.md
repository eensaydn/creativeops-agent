# Further Improvements

How I'd evolve this system for production scale.

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