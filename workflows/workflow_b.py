from tools.video_tool import generate_video
from langfuse import observe, get_client
import time
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


@observe()
async def run_workflow_b(image_base64: str, motion_prompt: str) -> dict:
    start_time = time.time()

    video_result = await generate_video(image_base64, motion_prompt)

    if "error" in video_result:
        return {"status": "error", "result": video_result["error"]}

    get_client().flush()
    return {
        "status": "completed",
        "video_base64": video_result["video_base64"],
        "format": video_result.get("format", "gif"),
        "model_used": video_result.get("model", "Wan2.1-I2V-14B"),
        "num_frames": video_result.get("num_frames", 16),
        "latency_seconds": video_result.get("latency_seconds"),
        "total_time": round(time.time() - start_time, 2),
    }