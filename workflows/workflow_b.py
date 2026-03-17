from agents import Runner
from my_agents.video_agent import video_agent
from tools.video_tool import generate_video
from tools.qa_tool import analyze_image
from langfuse.decorators import observe, langfuse_context
import time
import base64
import io
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

GPU_COST_PER_SECOND_A100 = 0.000694
AGENT_CALL_ESTIMATE = 0.001
FRAME_DURATION_MS = 100 


def validate_input_image(image_base64: str) -> dict:
    """Validate image dimensions and format before sending to video pipeline."""
    try:
        from PIL import Image
        img_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        return {"valid": False, "error": f"Invalid image data: {str(e)}"}

    width, height = img.size
    fmt = img.format or "unknown"

    if width < 64 or height < 64:
        return {"valid": False, "error": f"Image too small: {width}x{height}, minimum 64x64"}
    if width > 4096 or height > 4096:
        return {"valid": False, "error": f"Image too large: {width}x{height}, maximum 4096x4096"}
    if fmt.lower() not in ("png", "jpeg", "jpg", "webp", "bmp"):
        return {"valid": False, "error": f"Unsupported format: {fmt}"}

    return {"valid": True, "width": width, "height": height, "format": fmt}


def extract_first_frame(video_base64: str) -> str:
    """Extract first frame from GIF as PNG base64 for QA analysis."""
    try:
        from PIL import Image
        gif_bytes = base64.b64decode(video_base64)
        gif = Image.open(io.BytesIO(gif_bytes))
        gif.seek(0)

        frame = gif.convert("RGB")
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


@observe()
async def run_workflow_b(image_base64: str, motion_prompt: str) -> dict:
    start_time = time.time()
    costs = {"llm": 0, "gpu": 0}
    total_tokens = {"input": 0, "output": 0}

    validation = validate_input_image(image_base64)
    if not validation["valid"]:
        return {"status": "error", "result": validation["error"]}

    result = await Runner.run(video_agent, motion_prompt)
    enhanced_prompt = result.final_output
    costs["llm"] += AGENT_CALL_ESTIMATE

    video_result = await generate_video(image_base64, enhanced_prompt)

    if "error" in video_result:
        return {"status": "error", "result": video_result["error"]}

    gpu_latency = video_result.get("latency_seconds", 0)
    costs["gpu"] += gpu_latency * GPU_COST_PER_SECOND_A100

    num_frames = video_result.get("num_frames", 16)
    video_duration = round(num_frames * FRAME_DURATION_MS / 1000, 1)

    frame_base64 = extract_first_frame(video_result.get("video_base64", ""))
    qa_image = frame_base64 if frame_base64 else image_base64

    qa_prompt = f"Video frame from motion: {motion_prompt}. Check quality and motion coherence."
    qa_result = await analyze_image(qa_image, qa_prompt)
    qa_score = qa_result.get("overall_score", 0)

    qa_tokens = qa_result.get("token_usage", {})
    costs["llm"] += qa_tokens.get("cost", 0.002)
    total_tokens["input"] += qa_tokens.get("input", 0)
    total_tokens["output"] += qa_tokens.get("output", 0)

    total_cost = round(costs["llm"] + costs["gpu"], 4)
    langfuse_context.flush()

    return {
        "status": "completed",
        "video_base64": video_result["video_base64"],
        "format": video_result.get("format", "gif"),
        "model_used": video_result.get("model", "Wan2.1-I2V-14B"),
        "enhanced_prompt": enhanced_prompt,
        "num_frames": num_frames,
        "duration_seconds": video_duration,
        "input_validation": {
            "width": validation["width"],
            "height": validation["height"],
            "format": validation["format"],
        },
        "qa_score": qa_score,
        "qa_feedback": qa_result.get("feedback", ""),
        "latency_seconds": video_result.get("latency_seconds"),
        "total_time": round(time.time() - start_time, 2),
        "token_usage": total_tokens,
        "cost_breakdown": {
            "llm_cost": round(costs["llm"], 4),
            "gpu_cost": round(costs["gpu"], 4),
            "total_cost": total_cost,
        },
    }