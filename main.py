"""
Studio AI - Backend Server
Run with: python app.py

.env (project root) needs:
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=your_service_role_key
    SUPABASE_BUCKET=Img Store        # optional, this is the default
"""

import os, io, re, sys, json, mimetypes, subprocess, threading, random, time, zipfile, shutil, glob
from flask import Flask, request, jsonify, send_from_directory, send_file, abort
from dotenv import load_dotenv

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PROMPT_JSON = os.path.join(BASE_DIR, "Prompt", "prompt.json")
PROMPT_PY   = os.path.join(BASE_DIR, "Prompt", "prompt.py")
TRIGGER_PY  = os.path.join(BASE_DIR, "Kaggle", "trigger.py")
KAGGLE_PY   = os.path.join(BASE_DIR, "Kaggle", "kaggle.py")
DESIGN_DIR  = os.path.join(BASE_DIR, "Design")
OUTPUT_DIR  = os.path.join(DESIGN_DIR, "output")
KERNEL_ID   = "subhan1122/img-generator"

SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "Img Store")

os.makedirs(OUTPUT_DIR, exist_ok=True)
app = Flask(__name__, static_folder=DESIGN_DIR)

# Allow the website on Vercel to call this backend
try:
    from flask_cors import CORS
    CORS(app, origins=[
        "https://ai-img-generator-beta.vercel.app",
        "https://ai-img-generator-ccnazik3m-msubhan8661-6906s-projects.vercel.app",
        r"https://.*\.vercel\.app",   # all Vercel preview URLs
        "http://localhost:5000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
    ])
except ImportError:
    print("[WARN] flask-cors not installed (pip install flask-cors). Needed when the page is hosted elsewhere.")

RATIO_SIZES = {
    "1:1 Square":  (1024, 1024),
    "16:9 Wide":   (1920, 1080),
    "4:3 Classic": (1440, 1080),
    "3:4 Portrait":(1080, 1440),
    "9:16 Story":  (1080, 1920),
    "21:9 Cinema": (2560, 1080),
}

CURRENT_TARGET = {"w": 1024, "h": 1024}


def resolve_size(data):
    """Work out (width, height) from whatever the web page sends."""
    ratio = str(data.get("ratio", "")).strip()
    if ratio in RATIO_SIZES:
        return RATIO_SIZES[ratio]

    low = ratio.lower().replace("×", "x")
    m = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", low)          # "1920 x 1080"
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)\s*:\s*(\d+)", low)                    # "16:9" / "16:9 Wide"
    if m:
        token = f"{m.group(1)}:{m.group(2)}"
        for key, size in RATIO_SIZES.items():
            if key.split()[0] == token:
                return size

    try:                                                         # explicit width/height
        w, h = int(data.get("width")), int(data.get("height"))
        if w >= 256 and h >= 256:
            return w, h
    except (TypeError, ValueError):
        pass

    print(f"[WARN] Unknown ratio {ratio!r}, using 1024x1024")
    return 1024, 1024


def fit_to_size(path, w, h):
    """
    Safety net: make sure the saved image has the shape the user picked,
    even if Kaggle returned something different (center-crop + resize).
    """
    try:
        from PIL import Image
        with Image.open(path) as im:
            img = im.copy()
        if img.size == (w, h):
            return
        src_w, src_h = img.size
        target = w / h
        if abs(src_w / src_h - target) > 0.02:
            print(f"[WARN] Kaggle returned {src_w}x{src_h} but {w}x{h} was requested "
                  f"- cropping to the requested shape")
            if src_w / src_h > target:
                new_w = int(src_h * target)
                left = (src_w - new_w) // 2
                img = img.crop((left, 0, left + new_w, src_h))
            else:
                new_h = int(src_w / target)
                top = (src_h - new_h) // 2
                img = img.crop((0, top, src_w, top + new_h))
        img = img.resize((w, h), Image.LANCZOS)
        img.save(path)
        print(f"[IMAGE] Final size {w}x{h}")
    except Exception as e:
        print(f"[FIT ERROR] {e}")


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

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

# ─────────────────────────────────────────────────────────────
# Subprocess helper (UTF-8 safe on Windows)
# ─────────────────────────────────────────────────────────────

SUB_ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

KAGGLE_BIN = shutil.which("kaggle") or os.path.join(
    os.path.dirname(sys.executable), "kaggle.exe" if os.name == "nt" else "kaggle")


def run_cmd(cmd, timeout=None):
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env=SUB_ENV, cwd=BASE_DIR, timeout=timeout,
    )


# ─────────────────────────────────────────────────────────────
# Supabase helpers
# ─────────────────────────────────────────────────────────────

_sb_client = None


def get_bucket():
    global _sb_client
    if _sb_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing in .env")
        from supabase import create_client
        _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb_client.storage.from_(SUPABASE_BUCKET)


def upload_to_supabase(local_path, remote_name):
    """Upload a local PNG to the bucket and return its public URL."""
    bucket = get_bucket()
    with open(local_path, "rb") as f:
        bucket.upload(
            path=remote_name,
            file=f.read(),
            file_options={"content-type": "image/png", "upsert": "true"},
        )
    return bucket.get_public_url(remote_name).rstrip("?")


def latest_supabase_image():
    """Public URL of the newest image in the bucket, or None."""
    try:
        bucket = get_bucket()
        items = bucket.list("", {
            "limit": 20,
            "sortBy": {"column": "created_at", "order": "desc"},
        })
        for it in items:
            name = it.get("name", "")
            if name.lower().endswith(IMAGE_EXTS):
                return f"/image/{name}"
    except Exception as e:
        print(f"[SUPABASE LIST ERROR] {e}")
    return None


def publish_image(local_name):
    """
    Upload the downloaded image to Supabase and put the Supabase URL in
    gen_state so the website shows the image straight from the bucket.
    Falls back to the local copy if the upload fails.
    """
    local_path = os.path.join(OUTPUT_DIR, local_name)
    fit_to_size(local_path, CURRENT_TARGET["w"], CURRENT_TARGET["h"])
    try:
        gen_state["message"] = "Uploading image to Supabase..."
        url = upload_to_supabase(local_path, local_name)
        # The page loads the image from Supabase through this server (/image/<name>),
        # so it works whether the bucket is public or private.
        gen_state["image"]   = f"/image/{local_name}"
        gen_state["status"]  = "done"
        gen_state["message"] = "Image ready!"
        print(f"[SUPABASE] Stored -> {url}")
    except Exception as e:
        print(f"[SUPABASE ERROR] {e}")
        gen_state["image"]   = f"/output/{local_name}"
        gen_state["status"]  = "done"
        gen_state["message"] = f"Image ready (Supabase upload failed: {e})"


# ─────────────────────────────────────────────────────────────
# Inject the selected size into Kaggle/kaggle.py
# ─────────────────────────────────────────────────────────────

def inject_size(width, height):
    block = (
        "# <<SIZE_START>> auto-injected by app.py - do not edit manually\n"
        f"TARGET_WIDTH = {width}\n"
        f"TARGET_HEIGHT = {height}\n"
        "# <<SIZE_END>>"
    )
    with open(KAGGLE_PY, "r", encoding="utf-8-sig") as f:
        src = f.read()

    pattern = re.compile(r"# <<SIZE_START>>.*?# <<SIZE_END>>", re.S)
    if pattern.search(src):
        src = pattern.sub(lambda m: block, src)
    elif "# <<PROMPT_END>>" in src:
        src = src.replace("# <<PROMPT_END>>", "# <<PROMPT_END>>\n\n" + block, 1)
    else:
        raise RuntimeError("Could not find the prompt/size markers in Kaggle/kaggle.py")

    if "GEN_W" not in src:
        raise RuntimeError(
            "Kaggle/kaggle.py is still the OLD version (it has no size support). "
            "Replace it with the new kaggle.py and try again."
        )

    with open(KAGGLE_PY, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)


# ─────────────────────────────────────────────────────────────
# Kaggle CLI helpers
# ─────────────────────────────────────────────────────────────

def cli_kernel_status():
    """Return 'complete' | 'running' | 'queued' | 'error' | 'unknown'"""
    try:
        r = run_cmd([KAGGLE_BIN, "kernels", "status", KERNEL_ID], timeout=30)
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


LAST_DL_ERROR = ""


def cli_download_output():
    """
    Run: kaggle kernels output KERNEL_ID -p tmp   (retries 3 times)
    Extract zips, find the PNG, move it to OUTPUT_DIR.
    Returns PNG basename on success, None on failure (reason in LAST_DL_ERROR).
    """
    global LAST_DL_ERROR
    LAST_DL_ERROR = ""
    tmp = os.path.join(OUTPUT_DIR, "_dl")
    try:
        pngs = []
        for attempt in range(1, 4):
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp, exist_ok=True)

            r = run_cmd([KAGGLE_BIN, "kernels", "output", KERNEL_ID, "-p", tmp], timeout=180)
            print(f"[DOWNLOAD try {attempt}] code={r.returncode}")
            print(f"[DOWNLOAD stdout] {r.stdout.strip()[:300]}")
            print(f"[DOWNLOAD stderr] {r.stderr.strip()[:300]}")

            for zp in glob.glob(os.path.join(tmp, "*.zip")):
                with zipfile.ZipFile(zp) as z:
                    z.extractall(tmp)
                os.remove(zp)

            pngs = glob.glob(os.path.join(tmp, "**", "*.png"), recursive=True)
            if pngs:
                break

            LAST_DL_ERROR = ((r.stderr or r.stdout).strip()[-200:]
                             or "No image found in the Kaggle output "
                                "(the latest run may still be running, or was cancelled).")
            if attempt < 3:
                time.sleep(5)

        if not pngs:
            print(f"[DOWNLOAD] Failed: {LAST_DL_ERROR}")
            shutil.rmtree(tmp, ignore_errors=True)
            return None

        name = f"generated_{int(time.time())}.png"
        dest = os.path.join(OUTPUT_DIR, name)
        shutil.move(pngs[0], dest)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[DOWNLOAD] Saved -> {dest}")
        return name

    except Exception as e:
        LAST_DL_ERROR = str(e)
        print(f"[DOWNLOAD ERROR] {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        return None


def poll_then_download():
    """Background: poll until the kernel is complete, then download + store image."""
    gen_state["status"]  = "waiting"
    gen_state["message"] = "Kaggle GPU is generating your image..."

    interval   = 15
    max_secs   = 900      # 15 min hard cap
    elapsed    = 0
    saw_active = False    # have we seen the NEW run start?

    while elapsed < max_secs:
        time.sleep(interval)
        elapsed += interval
        ks = cli_kernel_status()
        m, s = divmod(elapsed, 60)

        if ks in ("running", "queued"):
            saw_active = True

        # Right after triggering, Kaggle may still report the OLD run as
        # complete. Wait until we see the new run start (or 90s pass).
        if ks == "complete" and not saw_active and elapsed < 90:
            gen_state["message"] = "Waiting for Kaggle to start the new run..."
            continue

        if ks == "complete":
            gen_state["message"] = "Kernel complete! Downloading image..."
            name = cli_download_output()
            if name:
                publish_image(name)
            else:
                gen_state["status"]  = "error"
                gen_state["message"] = f"Kernel finished but download failed: {LAST_DL_ERROR}"
            return

        elif ks == "error":
            gen_state["status"]  = "error"
            gen_state["message"] = "Kaggle kernel reported an error."
            return

        else:
            gen_state["message"] = f"Kaggle GPU rendering... {m}m {s}s elapsed"

    gen_state["status"]  = "error"
    gen_state["message"] = "Timed out (15 min). Use the Fetch button to download manually."


def do_download_now():
    """Background: download the latest output immediately and store it."""
    gen_state["status"]  = "waiting"
    gen_state["message"] = "Downloading image from Kaggle..."
    gen_state["image"]   = None

    name = cli_download_output()
    if name:
        publish_image(name)
    else:
        gen_state["status"]  = "error"
        gen_state["message"] = f"Download failed: {LAST_DL_ERROR or 'check that the Kaggle kernel has completed.'}"


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

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.\-]+$")


def get_image_bytes(name):
    """Image bytes from Supabase first, local copy as fallback."""
    if not SAFE_NAME.match(name) or not name.lower().endswith(IMAGE_EXTS):
        return None
    try:
        data = get_bucket().download(name)
        if data:
            return data
    except Exception as e:
        print(f"[SUPABASE DOWNLOAD ERROR] {name}: {e}")
    local = os.path.join(OUTPUT_DIR, name)
    if os.path.isfile(local):
        with open(local, "rb") as f:
            return f.read()
    return None


@app.route("/image/<name>")
def serve_image(name):
    """Show an image from Supabase on the website."""
    data = get_image_bytes(name)
    if data is None:
        abort(404)
    resp = send_file(io.BytesIO(data), mimetype=mimetypes.guess_type(name)[0] or "image/png")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@app.route("/download/<name>")
def download_image(name):
    """Download button: sends the image as a file attachment."""
    data = get_image_bytes(name)
    if data is None:
        abort(404)
    return send_file(io.BytesIO(data),
                     mimetype=mimetypes.guess_type(name)[0] or "image/png",
                     as_attachment=True, download_name=name)


@app.route("/last-image")
def last_image():
    if gen_state.get("image"):
        return jsonify({"image": gen_state["image"]})

    # Newest image from Supabase
    url = latest_supabase_image()
    if url:
        gen_state["image"] = url
        return jsonify({"image": url})

    # Fallback: newest local file
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
    gen_state["status"]  = "idle"
    gen_state["message"] = "Ready to create."
    gen_state["image"]   = None
    return jsonify({"ok": True})

@app.route("/generate", methods=["POST"])
def generate():
    if gen_state["status"] in ("waiting", "running"):
        return jsonify({"ok": False, "message": "Already generating. Please wait."}), 409

    data        = request.get_json(force=True)
    prompt_text = data.get("prompt", "").strip()
    ratio_name  = data.get("ratio", "1:1 Square")

    if not prompt_text:
        return jsonify({"ok": False, "message": "Prompt cannot be empty."}), 400

    width, height = resolve_size(data)
    CURRENT_TARGET["w"], CURRENT_TARGET["h"] = width, height
    print(f"[GENERATE] ratio from page = {ratio_name!r} -> {width}x{height}")
    with open(PROMPT_JSON, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt_text, "width": width, "height": height,
                   "ratio": ratio_name}, f, indent=4, ensure_ascii=False)

    def run_pipeline():
        gen_state["status"]  = "running"
        gen_state["message"] = "Injecting prompt into Kaggle script..."
        gen_state["image"]   = None

        try:
            # Step 1 - update kaggle.py with the new prompt
            r1 = run_cmd([sys.executable, PROMPT_PY])
            if r1.returncode != 0:
                raise RuntimeError(r1.stderr or r1.stdout)

            # Step 1b - inject the selected size (this is what fixes the ratio)
            inject_size(width, height)
            print(f"[PIPELINE] Size injected: {width}x{height}")

            gen_state["message"] = "Pushing script to Kaggle & triggering GPU..."

            # Step 2 - push & trigger kernel
            r2 = run_cmd([sys.executable, TRIGGER_PY])
            if r2.returncode != 0:
                raise RuntimeError(r2.stderr or r2.stdout)

            print(f"[PIPELINE] trigger.py stdout: {r2.stdout.strip()}")
            print("[PIPELINE] Kaggle kernel triggered. Polling for completion...")

            # Step 3 - poll until done, then download + store in Supabase
            poll_then_download()

        except Exception as exc:
            gen_state["status"]  = "error"
            gen_state["message"] = f"Error: {exc}"

    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({"ok": True, "message": "Pipeline started.",
                    "width": width, "height": height})


def check_supabase():
    try:
        get_bucket().list("", {"limit": 1})
        print(f"[SUPABASE] Connected. Bucket: {SUPABASE_BUCKET!r}")
    except Exception as e:
        print(f"[SUPABASE] NOT working: {e}")


if __name__ == "__main__":
    check_supabase()
    print("=" * 50)
    print("  Studio AI — http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, use_reloader=False)