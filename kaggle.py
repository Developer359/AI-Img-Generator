import os
import torch
import gc
from diffusers import AutoPipelineForText2Image
import zipfile

# Clear VRAM cache
torch.cuda.empty_cache()
gc.collect()

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

# Your batch of prompts
prompts = [
    "A stunning cinematic cyberpunk city skyline at sunset, intricate neon signs, glowing reflections, 8k resolution",
    "An epic fantasy castle on a floating mountain island during golden hour, highly detailed",
    "A sleek futuristic sports car driving through a vibrant neon city highway at night"
]

print(f"Starting batch generation of {len(prompts)} images...")
for i, prompt in enumerate(prompts):
    image = pipe(
        prompt=prompt,
        num_inference_steps=6,
        guidance_scale=2.0
    ).images[0]
    
    image.save(f"{output_dir}/img_{i+1}.png")
    print(f"Generated image {i+1}/{len(prompts)}")
    
    torch.cuda.empty_cache()

# Zip images for a clean download
print("Zipping output images...")
with zipfile.ZipFile("/kaggle/working/generated_images.zip", 'w') as zipf:
    for file in os.listdir(output_dir):
        if file.endswith('.png'):
            zipf.write(os.path.join(output_dir, file), file)

print("Batch complete!")