from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from agents import set_tracing_disabled
set_tracing_disabled(True)

from workflows.workflow_a import run_workflow_a
from workflows.workflow_b import run_workflow_b

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