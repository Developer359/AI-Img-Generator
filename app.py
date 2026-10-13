"""
Studio AI - Backend Server
Bridges the Design/index.html UI to the Kaggle GPU pipeline.
Run with: python app.py
"""

import os
import json
import subprocess
import threading
import random
from flask import Flask, request, jsonify, send_from_directory

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PROMPT_JSON = os.path.join(BASE_DIR, "Prompt", "prompt.json")
PROMPT_PY   = os.path.join(BASE_DIR, "Prompt", "prompt.py")
TRIGGER_PY  = os.path.join(BASE_DIR, "Kaggle", "trigger.py")
DESIGN_DIR  = os.path.join(BASE_DIR, "Design")
OUTPUT_DIR  = os.path.join(DESIGN_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder=DESIGN_DIR)

# Aspect ratio -> pixel dimensions
RATIO_SIZES = {
    "1:1 Square":  (1024, 1024),
    "16:9 Wide":   (1920, 1080),
    "4:3 Classic": (1440, 1080),
    "3:4 Portrait":(1080, 1440),
    "9:16 Story":  (1080, 1920),
    "21:9 Cinema": (2560, 1080),
}

# Shared generation state
gen_state = {
    "status": "idle",
    "message": "Ready to create.",
    "image": None,
}

SURPRISE_PROMPTS = [
    "A cinematic shot of a neon cyberpunk monolith in dense misty rain, dramatic rim lighting, photorealistic 8k, ultra-detailed.",
    "An ancient overgrown stone temple hidden inside a misty ethereal forest at dusk, giant glowing crystal lanterns, cascading waterfalls, luminescent flora, dark fantasy aesthetics.",
    "A lone astronaut standing on the surface of an alien ocean planet at twilight, two moons rising, bioluminescent waves, cinematic wide-angle, 8k.",
    "A futuristic floating city above the clouds at golden hour, glass towers, aerial gardens, dramatic volumetric lighting, concept art style.",
    "A dragon made entirely of aurora lights soaring over an arctic tundra, northern lights, hyperrealistic textures, epic fantasy.",
    "An underwater ancient lost city with glowing runes, schools of bioluminescent fish, massive coral structures, cinematic depth of field.",
    "A samurai standing in a bamboo forest during a heavy snowstorm, katana drawn, dynamic lighting, ink-wash painting meets photorealism.",
    "A vast desert with glass sand dunes reflecting a binary sunset, ruined spacecraft half-buried, cinematic sci-fi atmosphere.",
    "A Victorian steampunk airship harbor at night, dozens of brass vessels, gas lamp glow, fog, ultra-detailed.",
    "A micro-world inside a dewdrop on a leaf, tiny forests and mountains visible inside, macro photography, dreamy bokeh, 8k.",
]


@app.route("/")
def index():
    return send_from_directory(DESIGN_DIR, "index.html")


@app.route("/surprise")
def surprise():
    return jsonify({"prompt": random.choice(SURPRISE_PROMPTS)})


@app.route("/status")
def status():
    return jsonify(gen_state)


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/generate", methods=["POST"])
def generate():
    if gen_state["status"] == "running":
        return jsonify({"ok": False, "message": "Already generating, please wait..."}), 409

    data        = request.get_json(force=True)
    prompt_text = data.get("prompt", "").strip()
    ratio_name  = data.get("ratio", "1:1 Square")

    if not prompt_text:
        return jsonify({"ok": False, "message": "Prompt cannot be empty."}), 400

    width, height = RATIO_SIZES.get(ratio_name, (1024, 1024))

    # Write prompt + dimensions to Prompt/prompt.json
    payload = {
        "prompt": prompt_text,
        "width":  width,
        "height": height,
        "ratio":  ratio_name,
    }
    with open(PROMPT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    def run_pipeline():
        gen_state["status"]  = "running"
        gen_state["message"] = "Injecting prompt into Kaggle script..."
        gen_state["image"]   = None
        try:
            # Step 1: inject prompt into kaggle.py via prompt.py
            r1 = subprocess.run(
                ["python", PROMPT_PY],
                capture_output=True, text=True, cwd=BASE_DIR
            )
            if r1.returncode != 0:
                raise RuntimeError(r1.stderr or r1.stdout)

            gen_state["message"] = "Pushing to Kaggle GPU..."

            # Step 2: push + trigger kaggle kernel
            r2 = subprocess.run(
                ["python", TRIGGER_PY],
                capture_output=True, text=True, cwd=BASE_DIR
            )
            if r2.returncode != 0:
                raise RuntimeError(r2.stderr or r2.stdout)

            gen_state["status"]  = "done"
            gen_state["message"] = "Job submitted to Kaggle! Image will appear here when ready."
        except Exception as e:
            gen_state["status"]  = "error"
            gen_state["message"] = f"Error: {e}"

    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"ok": True, "message": "Generation started.", "width": width, "height": height})


if __name__ == "__main__":
    print("=" * 50)
    print("  Studio AI - Local Server")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, use_reloader=False)
