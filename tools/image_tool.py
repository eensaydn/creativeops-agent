import httpx
from config.settings import FLUX_ENDPOINT


async def generate_image(prompt: str, aspect_ratio: str = "1:1", seed: int = 42) -> dict:
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(FLUX_ENDPOINT, json={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
        })

    if response.status_code != 200:
        return {"error": f"Image generation failed: {response.status_code}"}

    return response.json()