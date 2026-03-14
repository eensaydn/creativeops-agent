import httpx
from config.settings import VIDEO_ENDPOINT


async def generate_video(image_base64: str, prompt: str, num_frames: int = 16) -> dict:
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(VIDEO_ENDPOINT, json={
            "image_base64": image_base64,
            "prompt": prompt,
            "num_frames": num_frames,
        })

    if response.status_code != 200:
        return {"error": f"Video generation failed: {response.status_code}"}

    return response.json()