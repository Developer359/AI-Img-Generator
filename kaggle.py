import subprocess
import sys
import gc

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import diffusers
    import accelerate
    import transformers
except ImportError:
    print("Installing required packages...")
    install("diffusers")
    install("transformers")
    install("accelerate")
    install("torch")

import torch
from diffusers import AutoPipelineForText2Image
import os

print("Cleaning up memory...")
torch.cuda.empty_cache()
gc.collect()

print("Loading SDXL Turbo pipeline optimized for Kaggle T4...")
# SDXL Turbo delivers high-end quality natively on 16GB VRAM GPUs without OOM errors
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sdxl-turbo", 
    torch_dtype=torch.float16, 
    variant="fp16"
)

pipe.to("cuda")
pipe.enable_attention_slicing()

os.makedirs("/kaggle/working/images", exist_ok=True)

prompts = [
    "A majestic cyberpunk city street at night, neon lights, highly detailed",
    "A cozy wooden cabin in a snowy mountain forest, cinematic lighting"
]

print("Starting generation batch...")
for i, prompt in enumerate(prompts):
    image = pipe(
        prompt=prompt,
        num_inference_steps=2,  # SDXL Turbo only needs 1-4 steps!
        guidance_scale=0.0,     # Turbo models use 0.0 guidance
    ).images[0]
    
    image.save(f"/kaggle/working/images/img_{i+1}.png")
    print(f"Generated image {i+1}/{len(prompts)}")
    
    torch.cuda.empty_cache()

print("Batch finished successfully with zero memory errors!")