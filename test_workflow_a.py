from dotenv import load_dotenv
load_dotenv()

from agents import set_tracing_disabled
set_tracing_disabled(True)

import asyncio
from workflows.workflow_a import run_workflow_a


async def main():
    brief = "Generate a cyberpunk portrait of a samurai in a neon-lit Tokyo alley"
    print("Starting Workflow A...")
    print(f"Brief: {brief}\n")

    result = await run_workflow_a(brief)

    for key, value in result.items():
        if key == "image_base64":
            print(f"image_base64: {str(value)[:100]}...")
        else:
            print(f"{key}: {value}")


asyncio.run(main())