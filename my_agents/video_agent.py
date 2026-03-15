from agents import Agent

video_agent = Agent(
    name="Video Generation Agent",
    instructions="""You are a video generation specialist.
Given an image description and a motion prompt, enhance the motion prompt for better video results.

Add details about camera movement, speed, lighting changes, and atmosphere.
Keep the original intent intact.
Only return the enhanced motion prompt text, nothing else.""",
    model="gpt-4o-mini",
)