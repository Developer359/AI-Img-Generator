import os
import gc
import math
import zipfile

import torch
from diffusers import AutoPipelineForText2Image
from PIL import Image

# Clear VRAM cache
torch.cuda.empty_cache()
gc.collect()

# <<PROMPT_START>> auto-injected by Prompt/prompt.py - do not edit manually
CURRENT_PROMPT = """A lone astronaut on an alien ocean planet at twilight, two moons rising, bioluminescent waves, cinematic 8k."""
# <<PROMPT_END>>

# <<SIZE_START>> auto-injected by app.py - do not edit manually
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
# <<SIZE_END>>

if not CURRENT_PROMPT.strip():
    raise ValueError("CRITICAL ERROR: CURRENT_PROMPT is empty! Run python Prompt/prompt.py first.")

print(f"Loaded prompt:\n-> {CURRENT_PROMPT}")
print(f"Requested size: {TARGET_WIDTH}x{TARGET_HEIGHT}")


def generation_size(w: int, h: int, budget: int = 1024 * 1024):
    """
    SDXL works best at ~1 megapixel. Keep the requested aspect ratio, keep
    the pixel count near 1MP, and make both sides multiples of 8.
    """
    scale = math.sqrt(budget / (w * h))
    gw = max(512, int(round(w * scale / 8)) * 8)
    gh = max(512, int(round(h * scale / 8)) * 8)
    return gw, gh


GEN_W, GEN_H = generation_size(TARGET_WIDTH, TARGET_HEIGHT)
print(f"Generating at {GEN_W}x{GEN_H}, final output {TARGET_WIDTH}x{TARGET_HEIGHT}")

model_id = "Lykon/dreamshaper-xl-v2-turbo"

print("Loading DreamShaper XL Turbo model...")
pipe = AutoPipelineForText2Image.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")

pipe.enable_attention_slicing()

output_dir = "/kaggle/working/images"
os.makedirs(output_dir, exist_ok=True)

print("Starting image generation...")
image = pipe(
    prompt=CURRENT_PROMPT,
    width=GEN_W,
    height=GEN_H,
    num_inference_steps=6,
    guidance_scale=2.0
).images[0]

# Resize to the exact size chosen on the website
if image.size != (TARGET_WIDTH, TARGET_HEIGHT):
    image = image.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)

image.save(f"{output_dir}/generated_img.png")
print(f"Image generated successfully! Final size: {image.size}")

# Zip output images for clean download
print("Zipping output images...")
with zipfile.ZipFile("/kaggle/working/generated_images.zip", 'w') as zipf:
    for file in os.listdir(output_dir):
        if file.endswith('.png'):
            zipf.write(os.path.join(output_dir, file), file)

print("Batch complete!")