"""
Studio AI - Backend Server
Run with: python app.py
"""

import os, json, subprocess, threading, random, time, zipfile, shutil, glob
from flask import Flask, request, jsonify, send_from_directory

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROMPT_JSON = os.path.join(BASE_DIR, "Prompt", "prompt.json")
PROMPT_PY   = os.path.join(BASE_DIR, "Prompt", "prompt.py")
TRIGGER_PY  = os.path.join(BASE_DIR, "Kaggle", "trigger.py")
DESIGN_DIR  = os.path.join(BASE_DIR, "Design")
OUTPUT_DIR  = os.path.join(DESIGN_DIR, "output")
KERNEL_ID   = "subhan1122/img-generator"

os.makedirs(OUTPUT_DIR, exist_ok=True)
app = Flask(__name__, static_folder=DESIGN_DIR)

RATIO_SIZES = {
    "1:1 Square":  (1024, 1024),
    "16:9 Wide":   (1920, 1080),
    "4:3 Classic": (1440, 1080),
    "3:4 Portrait":(1080, 1440),
    "9:16 Story":  (1080, 1920),
    "21:9 Cinema": (2560, 1080),
}

# status: idle | running | waiting | done | error
gen_state = {"status": "idle", "message": "Ready to create.", "image": None}

SURPRISE_PROMPTS = [
    "A cinematic shot of a neon cyberpunk monolith in dense misty rain, dramatic rim lighting, photorealistic 8k.",
    "An ancient overgrown stone temple hidden inside a misty ethereal forest at dusk, giant glowing crystal lanterns.",
    "A lone astronaut on an alien ocean planet at twilight, two moons rising, bioluminescent waves, cinematic 8k.",
    "A futuristic floating city above the clouds at golden hour, glass towers, aerial gardens, volumetric lighting.",
    "A dragon made entirely of aurora lights soaring over an arctic tundra, northern lights, hyperrealistic.",
    "An underwater ancient lost city with glowing runes, bioluminescent fish, massive coral structures.",
    "A samurai standing in a bamboo forest during a heavy snowstorm, katana drawn, dynamic lighting.",
    "A vast desert with glass sand dunes reflecting a binary sunset, ruined spacecraft half-buried.",
    "A Victorian steampunk airship harbor at night, dozens of brass vessels, gas lamp glow, fog.",
    "A micro-world inside a dewdrop on a leaf, tiny forests and mountains visible inside, 8k.",
]

# ─────────────────────────────────────────────────────────────
# Kaggle CLI helpers  (subprocess — reliable, already works)
# ─────────────────────────────────────────────────────────────

def cli_kernel_status():
    """Return 'complete' | 'running' | 'queued' | 'error' | 'unknown'"""
    try:
        r = subprocess.run(
            ["kaggle", "kernels", "status", KERNEL_ID],
            capture_output=True, text=True, timeout=30
        )
        out = (r.stdout + r.stderr).lower()
        print(f"[STATUS] {out.strip()[:120]}")
        if "complete" in out: return "complete"
        if "running"  in out: return "running"
        if "queue"    in out: return "queued"
        if "error"    in out or "cancel" in out: return "error"
        return "unknown"
    except Exception as e:
        print(f"[STATUS ERROR] {e}")
        return "unknown"


def cli_download_output():
    """
    Run: kaggle kernels output KERNEL_ID -p OUTPUT_DIR
    Extract any zips, find PNGs, move to OUTPUT_DIR.
    Returns PNG basename on success, None on failure.
    """
    tmp = os.path.join(OUTPUT_DIR, "_dl")
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)

        r = subprocess.run(
            ["kaggle", "kernels", "output", KERNEL_ID, "-p", tmp],
            capture_output=True, text=True, timeout=180
        )
        print(f"[DOWNLOAD stdout] {r.stdout.strip()[:300]}")
        print(f"[DOWNLOAD stderr] {r.stderr.strip()[:300]}")

        # Extract zips
        for zp in glob.glob(os.path.join(tmp, "*.zip")):
            with zipfile.ZipFile(zp) as z:
                z.extractall(tmp)
            os.remove(zp)

        # Find any PNG recursively
        pngs = glob.glob(os.path.join(tmp, "**", "*.png"), recursive=True)
        if not pngs:
            pngs = glob.glob(os.path.join(tmp, "*.png"))

        if not pngs:
            print("[DOWNLOAD] No PNG found.")
            shutil.rmtree(tmp, ignore_errors=True)
            return None

        name = f"generated_{int(time.time())}.png"
        dest = os.path.join(OUTPUT_DIR, name)
        shutil.move(pngs[0], dest)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[DOWNLOAD] Saved -> {dest}")
        return name

    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        return None


def poll_then_download():
    """Background: poll until kernel is complete, then download image."""
    gen_state["status"]  = "waiting"
    gen_state["message"] = "Kaggle GPU is generating your image..."

    interval = 15
    max_secs = 720   # 12 min hard cap
    elapsed  = 0

    while elapsed < max_secs:
        time.sleep(interval)
        elapsed += interval
        ks = cli_kernel_status()
        m, s = divmod(elapsed, 60)

        if ks == "complete":
            gen_state["message"] = "Kernel complete! Downloading image..."
            name = cli_download_output()
            if name:
                gen_state["image"]   = f"/output/{name}"
                gen_state["status"]  = "done"
                gen_state["message"] = "Image ready!"
            else:
                gen_state["status"]  = "error"
                gen_state["message"] = "Kernel finished but download failed. Use Fetch button."
            return

        elif ks == "error":
            gen_state["status"]  = "error"
            gen_state["message"] = "Kaggle kernel reported an error."
            return

        else:
            gen_state["message"] = f"Kaggle GPU rendering... {m}m {s}s elapsed"

    gen_state["status"]  = "error"
    gen_state["message"] = "Timed out (12 min). Use the Fetch button to download manually."


def do_download_now():
    """Background: immediately download without polling."""
    gen_state["status"]  = "waiting"
    gen_state["message"] = "Downloading image from Kaggle..."
    gen_state["image"]   = None

    name = cli_download_output()
    if name:
        gen_state["image"]   = f"/output/{name}"
        gen_state["status"]  = "done"
        gen_state["message"] = "Image ready!"
    else:
        gen_state["status"]  = "error"
        gen_state["message"] = "Download failed. Check that the Kaggle kernel has completed."


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

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

@app.route("/last-image")
def last_image():
    if gen_state.get("image"):
        return jsonify({"image": gen_state["image"]})
    pngs = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.png")),
                  key=os.path.getmtime, reverse=True)
    if pngs:
        p = f"/output/{os.path.basename(pngs[0])}"
        gen_state["image"] = p
        return jsonify({"image": p})
    return jsonify({"image": None})

@app.route("/fetch-now", methods=["POST"])
def fetch_now():
    """Download the latest Kaggle output right now (kernel must be complete)."""
    if gen_state["status"] == "waiting":
        return jsonify({"ok": False, "message": "Already downloading."}), 409
    threading.Thread(target=do_download_now, daemon=True).start()
    return jsonify({"ok": True, "message": "Download started."})

@app.route("/reset", methods=["POST"])
def reset():
    """Reset state to idle so user can generate again."""
    gen_state["status"]  = "idle"
    gen_state["message"] = "Ready to create."
    gen_state["image"]   = None
    return jsonify({"ok": True})

@app.route("/generate", methods=["POST"])
def generate():
    if gen_state["status"] == "waiting":
        return jsonify({"ok": False, "message": "Already generating. Please wait."}), 409

    data        = request.get_json(force=True)
    prompt_text = data.get("prompt", "").strip()
    ratio_name  = data.get("ratio", "1:1 Square")

    if not prompt_text:
        return jsonify({"ok": False, "message": "Prompt cannot be empty."}), 400

    width, height = RATIO_SIZES.get(ratio_name, (1024, 1024))
    with open(PROMPT_JSON, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt_text, "width": width, "height": height,
                   "ratio": ratio_name}, f, indent=4, ensure_ascii=False)

    def run_pipeline():
        gen_state["status"]  = "running"
        gen_state["message"] = "Injecting prompt into Kaggle script..."
        gen_state["image"]   = None

        # Clear old PNGs
        for old in glob.glob(os.path.join(OUTPUT_DIR, "*.png")):
            try: os.remove(old)
            except: pass

        try:
            # Step 1 – update kaggle.py with new prompt
            r1 = subprocess.run(["python", PROMPT_PY], capture_output=True,
                                 text=True, cwd=BASE_DIR)
            if r1.returncode != 0:
                raise RuntimeError(r1.stderr or r1.stdout)

            gen_state["message"] = "Pushing script to Kaggle & triggering GPU..."

            # Step 2 – push & trigger kernel
            r2 = subprocess.run(["python", TRIGGER_PY], capture_output=True,
                                 text=True, cwd=BASE_DIR)
            if r2.returncode != 0:
                raise RuntimeError(r2.stderr or r2.stdout)

            print(f"[PIPELINE] trigger.py stdout: {r2.stdout.strip()}")
            print("[PIPELINE] Kaggle kernel triggered. Polling for completion...")

            # Step 3 – poll until done, then download
            poll_then_download()

        except Exception as exc:
            gen_state["status"]  = "error"
            gen_state["message"] = f"Error: {exc}"

    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"ok": True, "message": "Pipeline started.",
                    "width": width, "height": height})


if __name__ == "__main__":
    print("=" * 50)
    print("  Studio AI — http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, use_reloader=False)
