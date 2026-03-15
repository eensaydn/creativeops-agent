from agents import Runner
from my_agents.video_agent import video_agent
from tools.video_tool import generate_video
from tools.qa_tool import analyze_image
from langfuse import observe, get_client
import time
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

GPU_COST_PER_SECOND_A100 = 0.000694


@observe()
async def run_workflow_b(image_base64: str, motion_prompt: str) -> dict:
    start_time = time.time()
    costs = {"llm": 0, "gpu": 0}

    result = await Runner.run(video_agent, motion_prompt)
    enhanced_prompt = result.final_output
    costs["llm"] += 0.001

    video_result = await generate_video(image_base64, enhanced_prompt)

    if "error" in video_result:
        return {"status": "error", "result": video_result["error"]}

    gpu_latency = video_result.get("latency_seconds", 0)
    costs["gpu"] += gpu_latency * GPU_COST_PER_SECOND_A100

    qa_result = await analyze_image(image_base64, f"Video based on: {motion_prompt}")
    qa_score = qa_result.get("overall_score", 0)
    costs["llm"] += 0.002

    total_cost = round(costs["llm"] + costs["gpu"], 4)
    get_client().flush()

    return {
        "status": "completed",
        "video_base64": video_result["video_base64"],
        "format": video_result.get("format", "gif"),
        "model_used": video_result.get("model", "Wan2.1-I2V-14B"),
        "enhanced_prompt": enhanced_prompt,
        "num_frames": video_result.get("num_frames", 16),
        "qa_score": qa_score,
        "qa_feedback": qa_result.get("feedback", ""),
        "latency_seconds": video_result.get("latency_seconds"),
        "total_time": round(time.time() - start_time, 2),
        "cost_breakdown": {
            "llm_cost": round(costs["llm"], 4),
            "gpu_cost": round(costs["gpu"], 4),
            "total_cost": total_cost,
        },
    }