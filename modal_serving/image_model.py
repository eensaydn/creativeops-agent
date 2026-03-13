import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field

load_dotenv()

mcp = FastMCP("ImageToolsServer")


class GenerateImageResult(BaseModel):
    model_used: str
    image_base64: str
    generation_params: dict
    latency_seconds: float
    endpoint_url: str


@mcp.tool
def generate_image(
    prompt: str = Field(..., description="Final image generation prompt"),
    aspect_ratio: str = Field(default="1:1", description="One of 1:1, 4:5, 16:9"),
    seed: int = Field(default=42, description="Random seed for reproducibility"),
) -> GenerateImageResult:
    endpoint = os.getenv("IMAGE_MODEL_ENDPOINT", "").strip()

    if not endpoint:
        raise ValueError("IMAGE_MODEL_ENDPOINT is missing in the environment.")

    response = requests.post(
        endpoint,
        json={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
        },
        timeout=300,
    )
    response.raise_for_status()

    data = response.json()

    return GenerateImageResult(
        model_used=data.get("model_used", "unknown"),
        image_base64=data["image_base64"],
        generation_params=data.get("generation_params", {}),
        latency_seconds=float(data.get("latency_seconds", 0.0)),
        endpoint_url=endpoint,
    )


if __name__ == "__main__":
    mcp.run()