import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

FLUX_ENDPOINT = "https://eensaydn--feraset-image-server-fluximageserver-generate.modal.run"
VIDEO_ENDPOINT = "https://eensaydn--wan-video-gen-generate-video.modal.run"

QA_THRESHOLD = 7.0
MAX_RETRIES = 2