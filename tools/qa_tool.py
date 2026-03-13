import openai
import json
from config.settings import OPENAI_API_KEY

client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


async def analyze_image(image_base64: str, original_prompt: str) -> dict:
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
    except:
        result = {
            "prompt_adherence": 5,
            "visual_quality": 5,
            "overall_score": 5.0,
            "feedback": text
        }

    return result