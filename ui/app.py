import gradio as gr
import asyncio
import base64
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents import set_tracing_disabled
set_tracing_disabled(True)

from workflows.workflow_a import run_workflow_a


def run_image_workflow(creative_brief):
    if not creative_brief:
        return None, "Please enter a creative brief"

    result = asyncio.run(run_workflow_a(creative_brief))

    if result.get("status") == "error":
        return None, f"Error: {result.get('result')}"

    img_bytes = base64.b64decode(result["image_base64"])
    img_path = "output.png"
    with open(img_path, "wb") as f:
        f.write(img_bytes)

    info = f"""Status: {result['status']}
QA Score: {result['qa_score']}/10
QA Feedback: {result['qa_feedback']}
Model: {result['model_used']}
Retries: {result['retries']}
Total Time: {result['total_time']}s"""

    return img_path, info


with gr.Blocks(title="CreativeOps Agent") as demo:
    gr.Markdown("# CreativeOps Agent")
    gr.Markdown("Multi-agent orchestrator for creative content generation")

    with gr.Tab("Image Generation (Workflow A)"):
        brief_input = gr.Textbox(label="Creative Brief", placeholder="e.g. A cyberpunk portrait of a samurai in a neon-lit Tokyo alley")
        generate_btn = gr.Button("Generate Image")
        output_image = gr.Image(label="Generated Image")
        output_info = gr.Textbox(label="Details", lines=6)

        generate_btn.click(
            fn=run_image_workflow,
            inputs=[brief_input],
            outputs=[output_image, output_info]
        )

    with gr.Tab("Video Generation (Workflow B)"):
        gr.Markdown("Coming soon")

if __name__ == "__main__":
    demo.launch()