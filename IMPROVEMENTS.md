# Further Improvements

How I'd evolve this system for production scale.

## FinOps & Cost Optimization

Right now cost tracking is basic — I calculate GPU cost from inference latency and track LLM token usage per call. This works for a demo but not at scale.

**Budget alerts and cost caps:** I'd add a `cost_limiter` middleware that checks accumulated cost before each tool call. Each workflow run would have a configurable budget (e.g. max $0.50 for image, max $1.00 for video). If a workflow is about to exceed its budget mid-execution (say on retry #2), it returns the best result so far instead of spending more. For alerts, I'd push cost events to a simple webhook — Slack notifications when daily spend crosses thresholds like $50, $100, $500.

**Cost-based routing between providers:** The system currently only uses FLUX for images and Wan2.1 for video. In production I'd add a routing layer that picks the cheapest provider that meets quality requirements. For example:
- Simple prompts (portraits, landscapes) → FLUX-schnell on L40S (~$0.003/image, 5s)
- Complex prompts (multi-subject scenes) → FLUX-dev on A100 (~$0.02/image, 15s)
- High-priority requests → replicate/fal.ai managed API as fallback (~$0.05/image but no cold starts)

The router would use the QA score history to learn which model handles which prompt types best. Start with simple rules, move to a lightweight classifier later.

**Dashboarding:** I'd build a Grafana dashboard pulling from Langfuse's API, showing:
- Cost per workflow type (daily/weekly trends)
- Average QA score and retry rate (tells us if we're wasting money on retries)
- Cost breakdown: LLM vs GPU vs total per request
- P95 latency per workflow
- Cold start frequency and impact on user wait time

The trace data in Langfuse already captures most of this. It's mainly a matter of querying it and putting it on a dashboard.

## Database Schema & Data Design

Currently everything is stateless — workflow results are returned to the caller and that's it. No persistence. For production:

**Database choice:** PostgreSQL for structured data (workflow metadata, QA results, cost records). It handles JSON fields well for flexible metadata, and it's battle-tested for transactional workloads. I'd use Supabase or Cloud SQL for managed hosting.

**Schema design:**

```
workflow_runs
├── id (uuid, PK)
├── workflow_type (enum: 'image', 'video')
├── status (enum: 'pending', 'processing', 'approved', 'failed', 'max_retries')
├── creative_brief (text)
├── user_id (uuid, FK → users)
├── created_at (timestamp)
├── completed_at (timestamp)
├── total_time_seconds (float)
└── metadata (jsonb — generation params, enhanced prompt, etc.)

generation_results
├── id (uuid, PK)
├── workflow_run_id (uuid, FK → workflow_runs)
├── attempt_number (int)
├── model_used (text)
├── asset_url (text — S3/GCS path)
├── generation_params (jsonb)
├── latency_seconds (float)
└── created_at (timestamp)

qa_results
├── id (uuid, PK)
├── generation_result_id (uuid, FK → generation_results)
├── overall_score (float)
├── prompt_adherence (float)
├── visual_quality (float)
├── feedback (text)
├── token_usage (jsonb — {input, output, cost})
└── created_at (timestamp)

cost_records
├── id (uuid, PK)
├── workflow_run_id (uuid, FK → workflow_runs)
├── cost_type (enum: 'llm', 'gpu', 'storage')
├── amount_usd (decimal)
├── provider (text — 'openai', 'modal-l40s', 'modal-a100', 'gcs')
├── token_count (int, nullable)
└── created_at (timestamp)
```

**Asset storage:** Generated images and videos go to Google Cloud Storage (or S3). The database stores the GCS path, not the base64 data. I'd set up:
- Hot storage (Standard class) for assets < 30 days old
- Cold storage (Nearline/Coldline) for older assets
- CDN (Cloud CDN or CloudFront) in front for serving to mobile clients
- Signed URLs with expiration for secure access

At scale with millions of users generating content daily, storage costs become significant. A cleanup job would delete unclaimed assets after 7 days and move saved ones to cheaper tiers.

## Service Architecture & Scalability

The current system is a monolith — FastAPI handles API, Gradio UI, and workflow orchestration all in one process. This works for a demo but has obvious scaling limits.

**Service decomposition:**

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API        │───>│  Task Queue      │───>│  Worker Pool    │
│   Gateway    │    │  (Redis/Celery    │    │  (image workers │
│   (FastAPI)  │    │   or Cloud Tasks) │    │   video workers)│
└─────────────┘    └──────────────────┘    └─────────────────┘
                                                     │
                                           ┌─────────┴──────────┐
                                           │  GPU Inference      │
                                           │  (Modal/RunPod)     │
                                           └─────────────────────┘
```

- **API Gateway**: Handles auth, rate limiting, request validation. Stateless, scales horizontally.
- **Task Queue**: Redis + Celery (or GCP Cloud Tasks). Image generation takes 5-15s, video takes 2-3min. These can't block an HTTP connection. Client gets a job ID and polls or uses webhooks.
- **Worker Pool**: Separate pools for image and video. Video workers need more memory and longer timeouts. Can scale independently based on queue depth.
- **GPU Inference**: Already on Modal (serverless). Would add RunPod as a failover provider.

**Queuing strategy:** Replace synchronous workflow execution with async job processing. The API returns immediately with a `job_id`. Client polls `/job/{id}/status` or registers a webhook. This handles the cold start problem — users don't stare at a loading screen for 45 seconds waiting for a GPU to warm up.

**Caching:**
- Redis cache for repeated prompts (same brief → same enhanced prompt, skip the LLM call)
- CDN cache for generated assets that are publicly shared
- Model warm-keeping: keep at least 1 GPU instance warm during peak hours (Modal's `min_containers` setting), accept cold starts during off-peak

**Rate limiting:**
- Per-user: 10 image requests/min, 3 video requests/min
- Global: circuit breaker if Modal/GPU provider error rate > 30% (back off for 60s)
- Cost-based: daily per-user budget cap (e.g. $5/day for free tier)

**Failover:**
- Primary image: FLUX on Modal → Fallback: FLUX on RunPod → Last resort: fal.ai managed API
- Primary video: Wan2.1 on Modal → Fallback: CogVideoX on RunPod
- LLM: OpenAI gpt-4o-mini → Fallback: Gemini Flash (if rate limits are resolved)

Each provider gets a health score based on recent error rate and latency. Router picks the best available one. If all self-hosted options are down, managed APIs are expensive but keep the service alive.

**What I'd build first:** The async job queue. Everything else (caching, failover, rate limiting) is important but the single biggest production gap right now is that video generation blocks the HTTP request for 2+ minutes. Async processing fixes the user experience and unlocks horizontal scaling at the same time.
