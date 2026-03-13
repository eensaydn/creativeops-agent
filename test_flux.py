import httpx

URL = "https://eensaydn--feraset-image-server-fluximageserver-generate.modal.run"

response = httpx.post(URL, json={
    "prompt": "a cute cat sitting on a chair",
    "aspect_ratio": "1:1",
    "seed": 42
}, timeout=300)

print("Status:", response.status_code)
print("Response:", response.text[:500])