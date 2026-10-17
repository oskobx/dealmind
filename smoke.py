import os, time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI(base_url="https://api.inference.crusoecloud.com/v1",
                api_key=os.environ["CRUSOE_API_KEY"])

MODELS = {
    "negotiator": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "supplier":   "Qwen/Qwen3.8-27B",
    "coach":      "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
}
for role, model in MODELS.items():
    t = time.time()
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a furniture supplier. Answer in one sentence."},
                  {"role": "user", "content": "Your best price per chair for 100 chairs?"}],
        max_tokens=600)
    print(f"--- {role} ({model}) {time.time()-t:.1f}s")
    print(r.choices[0].message.content)
