import openai
import json
import time
from config.settings import OPENAI_API_KEY
from langfuse.decorators import observe, langfuse_context

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

GPT4O_MINI_INPUT_COST = 0.00015  # per 1k tokens
GPT4O_MINI_OUTPUT_COST = 0.0006  # per 1k tokens


@observe(name="qa_analyze_image")
async def analyze_image(image_base64: str, original_prompt: str) -> dict:
    start = time.time()

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

    latency = round(time.time() - start, 2)

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = (input_tokens / 1000 * GPT4O_MINI_INPUT_COST) + (output_tokens / 1000 * GPT4O_MINI_OUTPUT_COST)

    langfuse_context.update_current_observation(
        model="gpt-4o-mini",
        usage={"input": input_tokens, "output": output_tokens},
        metadata={"latency_seconds": latency, "cost_usd": round(cost, 6)},
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

    result["token_usage"] = {"input": input_tokens, "output": output_tokens, "cost": round(cost, 6)}
    result["latency_seconds"] = latency
    return result
