import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FLUX_ENDPOINT = "https://eensaydn--feraset-image-server-fluximageserver-generate.modal.run"

QA_THRESHOLD = 7.0
MAX_RETRIES = 2