from agents import Runner
from my_agents.image_agent import image_agent
from config.settings import QA_THRESHOLD, MAX_RETRIES
from tools.image_tool import generate_image
from tools.qa_tool import analyze_image
import time


async def run_workflow_a(creative_brief: str) -> dict:
    start_time = time.time()
    retries = 0
    feedback = ""

    while retries <= MAX_RETRIES:
        if feedback:
            prompt = f"{creative_brief}. Previous feedback: {feedback}. Please improve."
        else:
            prompt = creative_brief

        result = await Runner.run(image_agent, prompt)
        enhanced_prompt = result.final_output

        image_result = await generate_image(enhanced_prompt)

        if "error" in image_result:
            return {"status": "error", "result": image_result["error"], "retries": retries}

        qa_result = await analyze_image(image_result["image_base64"], creative_brief)
        score = qa_result.get("overall_score", 0)

        if score >= QA_THRESHOLD:
            return {
                "status": "approved",
                "image_base64": image_result["image_base64"],
                "model_used": image_result.get("model_used", "FLUX.1-schnell"),
                "generation_params": image_result.get("generation_params", {}),
                "qa_score": score,
                "qa_feedback": qa_result.get("feedback", ""),
                "retries": retries,
                "total_time": round(time.time() - start_time, 2),
            }
        else:
            feedback = qa_result.get("feedback", "Quality not sufficient")
            retries += 1

    return {
        "status": "max_retries_reached",
        "image_base64": image_result["image_base64"],
        "model_used": image_result.get("model_used", "FLUX.1-schnell"),
        "generation_params": image_result.get("generation_params", {}),
        "qa_score": score,
        "qa_feedback": qa_result.get("feedback", ""),
        "retries": retries,
        "total_time": round(time.time() - start_time, 2),
    }