from agents import Agent
from my_agents.image_agent import image_agent
from my_agents.qa_agent import qa_agent

orchestrator_agent = Agent(
    name="Orchestrator Agent",
    instructions="""You are the orchestrator of a creative content pipeline.

When you receive a creative brief:
1. Analyze the brief and extract style, subject, and environment details
2. Hand off to the Image Generation Agent with an enhanced prompt
3. Once you get the image back, hand off to the QA Agent for review
4. If QA score is below 7.0, ask Image Generation Agent to regenerate with QA feedback (max 2 retries)
5. Return the final result with all metadata

Always include in your final response: model_used, generation_params, qa_score, and image_base64.""",
    handoffs=[image_agent, qa_agent],
    model="gpt-4o-mini",
)