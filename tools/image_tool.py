import httpx
import time
from config.settings import FLUX_ENDPOINT
from langfuse.decorators import observe, langfuse_context


@observe(name="generate_image")
async def generate_image(prompt: str, aspect_ratio: str = "1:1", seed: int = 42) -> dict:
    start = time.time()

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(FLUX_ENDPOINT, json={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
        })

    latency = round(time.time() - start, 2)

    if response.status_code != 200:
        langfuse_context.update_current_observation(
            metadata={"error": response.status_code, "latency_seconds": latency},
        )
        return {"error": f"Image generation failed: {response.status_code}"}

    result = response.json()
    gpu_latency = result.get("latency_seconds", latency)

    langfuse_context.update_current_observation(
        metadata={
            "model": result.get("model_used", "FLUX.1-schnell"),
            "latency_seconds": gpu_latency,
            "endpoint": FLUX_ENDPOINT,
        },
    )

    return result
