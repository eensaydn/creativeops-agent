import modal
import base64
import io
import time

app = modal.App("wan-video-gen")

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch",
    "diffusers",
    "transformers",
    "accelerate",
    "sentencepiece",
    "Pillow",
    "fastapi[standard]",
    "ftfy",
)

model_cache = modal.Volume.from_name("video-model-cache", create_if_missing=True)


@app.cls(
    gpu="A100-80GB",
    scaledown_window=60,
    image=image,
    timeout=900,
    volumes={"/models": model_cache},
    secrets=[modal.Secret.from_name("huggingface-secret", required_keys=["HF_TOKEN"])],
)
class WanVideoModel:
    @modal.enter()
    def load_model(self):
        import torch
        import os
        from diffusers import WanImageToVideoPipeline

        self.pipe = WanImageToVideoPipeline.from_pretrained(
            "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
            torch_dtype=torch.float16,
            cache_dir="/models",
            token=os.environ["HF_TOKEN"],
        )
        self.pipe.enable_model_cpu_offload()

    @modal.method()
    def generate(self, image_base64: str, prompt: str, num_frames: int = 16):
        from PIL import Image as PILImage

        img_bytes = base64.b64decode(image_base64)
        input_image = PILImage.open(io.BytesIO(img_bytes)).resize((832, 480))

        started = time.perf_counter()

        output = self.pipe(
            image=input_image,
            prompt=prompt,
            num_frames=num_frames,
            guidance_scale=5.0,
            num_inference_steps=20,
            output_type="pil",
        )

        frames = output.frames[0]
        video_buffer = io.BytesIO()
        frames[0].save(
            video_buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
        )
        video_base64 = base64.b64encode(video_buffer.getvalue()).decode("utf-8")

        latency = round(time.perf_counter() - started, 2)

        return {
            "video_base64": video_base64,
            "format": "gif",
            "num_frames": num_frames,
            "latency_seconds": latency,
            "model": "Wan2.1-I2V-14B-480P",
        }


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def generate_video(request: dict):
    image_base64 = request.get("image_base64", "")
    prompt = request.get("prompt", "")
    num_frames = request.get("num_frames", 16)

    model = WanVideoModel()
    result = model.generate.remote(image_base64, prompt, num_frames)
    return result