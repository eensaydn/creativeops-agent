from agents import Agent, function_tool
from tools.qa_tool import analyze_image


@function_tool
async def review_image(image_base64: str, original_prompt: str) -> dict:
    result = await analyze_image(image_base64, original_prompt)
    return result


qa_agent = Agent(
    name="QA Agent",
    instructions="""You are a quality assurance specialist for AI-generated images.
When given an image and the original prompt, use the review_image tool to analyze it.

Return the analysis result as-is including prompt_adherence, visual_quality, overall_score and feedback.""",
    tools=[review_image],
    model="gpt-4o-mini",
)