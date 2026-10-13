import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the official Google GenAI client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def enhance_prompt_for_dreamshaper(dummy_prompt: str) -> str:
    """
    Takes a simple dummy prompt and uses Gemini to craft a sharp, 
    concise, and high-impact prompt optimized specifically for DreamShaper XL Turbo.
    """
    system_instruction = (
        "You are an expert AI prompt engineer specializing in DreamShaper XL Turbo and SDXL models. "
        "Your job is to take a simple user prompt and expand it into a concise, punchy, highly effective prompt "
        "optimized for fast step generation. Focus on key visual elements, dramatic lighting, style, and sharp details. "
        "Keep it concise—avoid overly long, wordy paragraphs. Output only the enhanced prompt text with no conversational filler."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Enhance this prompt for DreamShaper XL Turbo: {dummy_prompt}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
    )
    
    return response.text.strip()

if __name__ == "__main__":
    # Path to prompt.json inside the Prompt folder
    json_path = "Prompt/prompt.json"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
    else:
        # 1. Load the original prompt from prompt.json
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        original_prompt = data.get("prompt", "")
        
        if not original_prompt:
            print("Error: No 'prompt' found in prompt.json!")
        else:
            print(f"Original Prompt: {original_prompt}\n")
            print("Enhancing with Gemini for DreamShaper XL Turbo...")
            
            # 2. Enhance the prompt using Gemini
            enhanced = enhance_prompt_for_dreamshaper(original_prompt)
            print(f"\nEnhanced DreamShaper Prompt:\n{enhanced}")
            
            # 3. Update the data dictionary with the final enhanced prompt
            data["prompt"] = enhanced
            
            # 4. Save it BACK into Prompt/prompt.json (Overwriting it)
            with open(json_path, "w", encoding="utf-8") as outfile:
                json.dump(data, outfile, indent=4)
                
            print(f"\nSuccessfully updated {json_path} with the final enhanced prompt!")