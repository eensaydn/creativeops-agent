from agents import Runner
from my_agents.image_agent import image_agent
from config.settings import QA_THRESHOLD, MAX_RETRIES
from tools.image_tool import generate_image
from tools.qa_tool import analyze_image
from langfuse.decorators import observe, langfuse_context
import time
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

GPU_COST_PER_SECOND_L40S = 0.000542
AGENT_CALL_ESTIMATE = 0.001 


@observe()
async def run_workflow_a(creative_brief: str) -> dict:
    start_time = time.time()
    retries = 0
    feedback = ""
    costs = {"llm": 0, "gpu": 0}
    total_tokens = {"input": 0, "output": 0}

    while retries <= MAX_RETRIES:
        if feedback:
            prompt = f"{creative_brief}. Previous feedback: {feedback}. Please improve."
        else:
            prompt = creative_brief

        result = await Runner.run(image_agent, prompt)
        enhanced_prompt = result.final_output
        costs["llm"] += AGENT_CALL_ESTIMATE

        image_result = await generate_image(enhanced_prompt)

        if "error" in image_result:
            return {"status": "error", "result": image_result["error"], "retries": retries}

        gpu_latency = image_result.get("latency_seconds", 0)
        costs["gpu"] += gpu_latency * GPU_COST_PER_SECOND_L40S

        qa_result = await analyze_image(image_result["image_base64"], creative_brief)
        score = qa_result.get("overall_score", 0)

        qa_tokens = qa_result.get("token_usage", {})
        costs["llm"] += qa_tokens.get("cost", 0.002)
        total_tokens["input"] += qa_tokens.get("input", 0)
        total_tokens["output"] += qa_tokens.get("output", 0)

        if score >= QA_THRESHOLD:
            total_cost = round(costs["llm"] + costs["gpu"], 4)
            langfuse_context.flush()
            return {
                "status": "approved",
                "image_base64": image_result["image_base64"],
                "model_used": image_result.get("model_used", "FLUX.1-schnell"),
                "generation_params": image_result.get("generation_params", {}),
                "qa_score": score,
                "qa_feedback": qa_result.get("feedback", ""),
                "retries": retries,
                "total_time": round(time.time() - start_time, 2),
                "token_usage": total_tokens,
                "cost_breakdown": {
                    "llm_cost": round(costs["llm"], 4),
                    "gpu_cost": round(costs["gpu"], 4),
                    "total_cost": total_cost,
                },
            }
        else:
            feedback = qa_result.get("feedback", "Quality not sufficient")
            retries += 1

    total_cost = round(costs["llm"] + costs["gpu"], 4)
    langfuse_context.flush()
    return {
        "status": "max_retries_reached",
        "image_base64": image_result["image_base64"],
        "model_used": image_result.get("model_used", "FLUX.1-schnell"),
        "generation_params": image_result.get("generation_params", {}),
        "qa_score": score,
        "qa_feedback": qa_result.get("feedback", ""),
        "retries": retries,
        "total_time": round(time.time() - start_time, 2),
        "token_usage": total_tokens,
        "cost_breakdown": {
            "llm_cost": round(costs["llm"], 4),
            "gpu_cost": round(costs["gpu"], 4),
            "total_cost": total_cost,
        },
    }