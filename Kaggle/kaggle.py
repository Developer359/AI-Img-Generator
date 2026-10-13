import os
import torch
import gc
from diffusers import AutoPipelineForText2Image
import zipfile

# Clear VRAM cache
torch.cuda.empty_cache()
gc.collect()

# <<PROMPT_START>> auto-injected by Prompt/prompt.py - do not edit manually
CURRENT_PROMPT = """A lone astronaut standing on the surface of an alien ocean planet at twilight, two moons rising, bioluminescent waves, cinematic wide-angle, 8k."""
# <<PROMPT_END>>

if not CURRENT_PROMPT.strip():
    raise ValueError("CRITICAL ERROR: CURRENT_PROMPT is empty! Run python Prompt/prompt.py first.")

print(f"Loaded prompt:\n-> {CURRENT_PROMPT}")

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
    num_inference_steps=6,
    guidance_scale=2.0
).images[0]

image.save(f"{output_dir}/generated_img.png")
print("Image generated successfully!")

# Zip output images for clean download
print("Zipping output images...")
with zipfile.ZipFile("/kaggle/working/generated_images.zip", 'w') as zipf:
    for file in os.listdir(output_dir):
        if file.endswith('.png'):
            zipf.write(os.path.join(output_dir, file), file)

print("Batch complete!")