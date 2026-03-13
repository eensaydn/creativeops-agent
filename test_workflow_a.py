import os
os.environ["OPENAI_API_KEY"] = "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"

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