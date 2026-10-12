import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the official Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def enhance_prompt_for_flux(dummy_prompt: str) -> str:
    """
    Takes a simple dummy prompt and uses Gemini to craft a rich, 
    highly detailed prompt optimized specifically for FLUX.1.
    """
    system_instruction = (
        "You are an expert AI prompt engineer specializing in FLUX.1. "
        "Your job is to take a simple, short user prompt and expand it into a rich, descriptive, "
        "photorealistic prompt. Focus heavily on lighting, textures, cinematic composition, camera details, "
        "and rich environment descriptions. Do not add conversational filler; output only the enhanced prompt text."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Enhance this prompt for FLUX.1: {dummy_prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
    )
    
    return response.text.strip()

if __name__ == "__main__":
    # Test with a simple dummy prompt
    dummy_input = "a cyberpunk cat wearing sunglasses"
    
    print(f"Original Dummy Prompt: {dummy_input}\n")
    print("Enhancing with Gemini for FLUX.1...")
    
    enhanced = enhance_prompt_for_flux(dummy_input)
    
    print(f"\nEnhanced FLUX Prompt:\n{enhanced}")