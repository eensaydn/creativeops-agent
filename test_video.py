from dotenv import load_dotenv
load_dotenv()

import asyncio
from tools.image_tool import generate_image
from tools.video_tool import generate_video


async def main():
    print("Step 1: Generating image...")
    image_result = await generate_image("a calm ocean with sunset")

    if "error" in image_result:
        print(f"Image error: {image_result['error']}")
        return

    print("Image generated!")
    print("Step 2: Generating video...")

    video_result = await generate_video(
        image_base64=image_result["image_base64"],
        prompt="slow camera pan to the right with gentle waves",
        num_frames=16,
    )

    if "error" in video_result:
        print(f"Video error: {video_result['error']}")
        return

    print(f"Video generated!")
    print(f"Model: {video_result.get('model')}")
    print(f"Frames: {video_result.get('num_frames')}")
    print(f"Latency: {video_result.get('latency_seconds')}s")


asyncio.run(main())