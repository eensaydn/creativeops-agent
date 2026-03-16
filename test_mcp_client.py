"""Quick test to show MCP client can trigger tools on the MCP server."""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/media_server.py"]
    )

    print("Connecting to MCP server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # list available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # call generate_image via MCP
            print("\nCalling generate_image via MCP...")
            result = await session.call_tool("generate_image", {
                "prompt": "a simple red circle on white background",
                "aspect_ratio": "1:1",
                "seed": 42,
            })

            data = json.loads(result.content[0].text)
            print(f"Model: {data.get('model_used', 'unknown')}")
            print(f"Latency: {data.get('latency_seconds', 'unknown')}s")
            print(f"Image base64 length: {len(data.get('image_base64', ''))} chars")
            print("MCP tool call successful!")


asyncio.run(main())