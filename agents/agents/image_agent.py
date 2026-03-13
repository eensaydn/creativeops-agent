from agents import Agent, function_tool
from tools.image_tool import generate_image


@function_tool
async def create_image(prompt: str, aspect_ratio: str = "1:1", seed: int = 42) -> dict:
    result = await generate_image(prompt, aspect_ratio, seed)
    return result


image_agent = Agent(
    name="Image Generation Agent",
    instructions="""You are an image generation specialist. When given a creative brief, 
you enhance the prompt for better results and call the create_image tool.

When enhancing prompts:
- Add details about lighting, composition, and style
- Keep the original intent intact
- Be specific about visual elements

After generating, return the full result including model_used, generation_params and image_base64.""",
    tools=[create_image],
    model="gpt-4o-mini",
)