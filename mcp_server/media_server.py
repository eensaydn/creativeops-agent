from mcp.server.fastmcp import FastMCP
import httpx
import openai
import json
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("media-tools")

FLUX_ENDPOINT = "https://eensaydn--feraset-image-server-fluximageserver-generate.modal.run"
VIDEO_ENDPOINT = "https://eensaydn--wan-video-gen-generate-video.modal.run"


@mcp.tool()
async def generate_image(prompt: str, aspect_ratio: str = "1:1", seed: int = 42) -> dict:
    """Generate an image using FLUX model on Modal."""
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(FLUX_ENDPOINT, json={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
        })

    if response.status_code != 200:
        return {"error": f"Failed: {response.status_code}"}

    return response.json()


@mcp.tool()
async def generate_video(image_base64: str, prompt: str, num_frames: int = 16) -> dict:
    """Generate a video from an image using Wan2.1 model on Modal."""
    async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
        response = await client.post(VIDEO_ENDPOINT, json={
            "image_base64": image_base64,
            "prompt": prompt,
            "num_frames": num_frames,
        })

    if response.status_code != 200:
        return {"error": f"Failed: {response.status_code}"}

    return response.json()


@mcp.tool()
async def analyze_image(image_base64: str, original_prompt: str) -> dict:
    """Analyze an AI-generated image for quality using vision model."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze this AI-generated image based on the original prompt.

Original prompt: {original_prompt}

Rate the image from 1-10 on these criteria:
- Prompt adherence: Does it match what was requested?
- Visual quality: Is it well-composed and detailed?
- Overall score: Your final rating

Respond in this exact JSON format only, no other text:
{{"prompt_adherence": 8, "visual_quality": 7, "overall_score": 7.5, "feedback": "brief feedback here"}}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": "low"
                        }
                    }
                ]
            }
        ],
        max_tokens=200
    )

    try:
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
    except Exception:
        result = {
            "prompt_adherence": 5,
            "visual_quality": 5,
            "overall_score": 5.0,
            "feedback": text
        }

    return result


if __name__ == "__main__":
    mcp.run()
