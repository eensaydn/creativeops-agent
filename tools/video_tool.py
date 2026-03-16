import httpx
import time
from config.settings import VIDEO_ENDPOINT
from langfuse.decorators import observe, langfuse_context


@observe(name="generate_video")
async def generate_video(image_base64: str, prompt: str, num_frames: int = 16) -> dict:
    start = time.time()

    async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
        response = await client.post(VIDEO_ENDPOINT, json={
            "image_base64": image_base64,
            "prompt": prompt,
            "num_frames": num_frames,
        })

    latency = round(time.time() - start, 2)

    if response.status_code != 200:
        langfuse_context.update_current_observation(
            metadata={"error": response.status_code, "latency_seconds": latency},
        )
        return {"error": f"Video generation failed: {response.status_code}"}

    result = response.json()
    gpu_latency = result.get("latency_seconds", latency)

    langfuse_context.update_current_observation(
        metadata={
            "model": result.get("model", "Wan2.1-I2V-14B"),
            "latency_seconds": gpu_latency,
            "num_frames": result.get("num_frames", num_frames),
            "endpoint": VIDEO_ENDPOINT,
        },
    )

    return result
