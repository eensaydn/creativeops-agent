from agents import Agent

image_agent = Agent(
    name="Image Generation Agent",
    instructions="""You are an image generation prompt engineer. 
Given a creative brief, enhance it into a detailed image generation prompt.

Add details about lighting, composition, style, colors, and mood.
Keep the original intent intact.
Only return the enhanced prompt text, nothing else.""",
    model="gpt-4o-mini",
)