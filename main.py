from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from agents import set_tracing_disabled
set_tracing_disabled(True)

from workflows.workflow_a import run_workflow_a
from workflows.workflow_b import run_workflow_b

import gradio as gr
import asyncio
import base64

app = FastAPI(title="CreativeOps Agent")


class ImageRequest(BaseModel):
    creative_brief: str
    aspect_ratio: str = "1:1"
    seed: int = 42


class VideoRequest(BaseModel):
    image_base64: str
    motion_prompt: str
    num_frames: int = 16


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/workflow/image")
async def workflow_image(request: ImageRequest):
    result = await run_workflow_a(request.creative_brief)
    return result


@app.post("/workflow/video")
async def workflow_video(request: VideoRequest):
    result = await run_workflow_b(request.image_base64, request.motion_prompt)
    return result


def run_image_workflow(creative_brief):
    if not creative_brief:
        return None, "Please enter a creative brief"
    result = asyncio.run(run_workflow_a(creative_brief))
    if result.get("status") == "error":
        return None, f"Error: {result.get('result')}"
    img_bytes = base64.b64decode(result["image_base64"])
    with open("/tmp/output.png", "wb") as f:
        f.write(img_bytes)
    info = f"""Status: {result['status']}
QA Score: {result['qa_score']}/10
QA Feedback: {result['qa_feedback']}
Model: {result['model_used']}
Retries: {result['retries']}
Total Time: {result['total_time']}s"""
    return "/tmp/output.png", info


def run_video_workflow(image_file, motion_prompt):
    if image_file is None or not motion_prompt:
        return None, "Please upload an image and enter a motion prompt"
    with open(image_file, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    result = asyncio.run(run_workflow_b(image_base64, motion_prompt))
    if result.get("status") == "error":
        return None, f"Error: {result.get('result')}"
    video_bytes = base64.b64decode(result["video_base64"])
    with open("/tmp/output.gif", "wb") as f:
        f.write(video_bytes)
    info = f"""Status: {result['status']}
Model: {result['model_used']}
Frames: {result['num_frames']}
Latency: {result.get('latency_seconds', 'N/A')}s
Total Time: {result['total_time']}s"""
    return "/tmp/output.gif", info


with gr.Blocks(title="CreativeOps Agent") as demo:
    gr.Markdown("# CreativeOps Agent")

    with gr.Tab("Image Generation"):
        brief_input = gr.Textbox(label="Creative Brief", placeholder="e.g. A cyberpunk samurai in neon-lit Tokyo")
        generate_btn = gr.Button("Generate Image")
        output_image = gr.Image(label="Generated Image")
        output_info = gr.Textbox(label="Details", lines=6)
        generate_btn.click(fn=run_image_workflow, inputs=[brief_input], outputs=[output_image, output_info])

    with gr.Tab("Video Generation"):
        image_input = gr.Image(label="Upload Image", type="filepath")
        motion_input = gr.Textbox(label="Motion Prompt", placeholder="e.g. Slow camera pan to the right")
        video_btn = gr.Button("Generate Video")
        output_video = gr.Image(label="Generated Video (GIF)")
        video_info = gr.Textbox(label="Details", lines=5)
        video_btn.click(fn=run_video_workflow, inputs=[image_input, motion_input], outputs=[output_video, video_info])

app = gr.mount_gradio_app(app, demo, path="/ui")