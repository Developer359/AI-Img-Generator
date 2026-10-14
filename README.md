<div align="center">

# 🎨 Studio AI — Free GPU Image Generator

### Generate stunning, high-resolution AI images using **free Kaggle GPUs** — no paid API required.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Supabase](https://img.shields.io/badge/Supabase-Storage-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Kaggle](https://img.shields.io/badge/Kaggle-Free_GPU-20BEFF?style=for-the-badge&logo=kaggle&logoColor=white)](https://kaggle.com)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![Railway](https://img.shields.io/badge/Backend-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

**Model Used:** Lykon/dreamshaper-xl-v2-turbo (Stable Diffusion XL Turbo)

</div>

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Problem It Solves](#-problem-it-solves)
3. [Features](#-features)
4. [Tech Stack](#-tech-stack)
5. [Project Architecture](#-project-architecture)
6. [Folder Structure](#-folder-structure)
7. [How the Pipeline Works](#-how-the-pipeline-works)
8. [Installation and Local Setup](#-installation-and-local-setup)
9. [Environment Variables](#-environment-variables)
10. [Kaggle Setup](#-kaggle-setup)
11. [Supabase Setup](#-supabase-setup)
12. [Deployment Guide](#-deployment-guide)
13. [API Reference](#-api-reference)
14. [Supported Aspect Ratios](#-supported-aspect-ratios)
15. [Utility Scripts](#-utility-scripts)
16. [Troubleshooting](#-troubleshooting)
17. [Contributing](#-contributing)

---

## 🌟 Overview

**Studio AI** is a full-stack web application that lets you generate high-resolution AI images **completely free** — no paid GPU, no OpenAI API key, no subscription needed.

The trick: It uses **Kaggle's free GPU tier** (Tesla T4/P100) to run a Stable Diffusion XL model in the cloud. You type a prompt in the browser, click Generate, and the backend:

1. Injects your prompt into a Kaggle notebook script
2. Triggers a Kaggle kernel (GPU job) remotely via the Kaggle CLI
3. Polls until the job completes (usually 1-3 minutes)
4. Downloads the generated PNG
5. Uploads it to **Supabase Storage** for persistent access
6. Streams the result back to your browser

The frontend is a beautifully styled dark-mode Studio UI served by Flask (or hosted statically on Vercel), and the backend runs on **Railway** (or any Python host).

---

## 🧩 Problem It Solves

| Problem | Studio AI Solution |
|---|---|
| Image generation APIs (DALL-E, Midjourney) cost money | Uses **free Kaggle GPU** — 30 hours/week at no charge |
| Running Stable Diffusion locally needs a powerful GPU | Offloads all compute to **Kaggle's cloud GPU** |
| Generated images get lost after session ends | Auto-uploads every image to **Supabase Storage** |
| Complex CLI workflow to trigger Kaggle notebooks | One-click **Generate button** in the browser handles everything |
| Hard-coded image sizes in scripts | **Dynamic aspect ratio injection** — choose from 6 presets at runtime |

---

## ✨ Features

- 🎨 **Beautiful Dark UI** — Studio-grade design with purple accent theme, glassmorphism panels, and smooth animations
- ⚡ **Free GPU Generation** — Runs DreamShaper XL v2 Turbo on Kaggle's free Tesla T4
- 🖼️ **6 Aspect Ratios** — Square, Wide, Classic, Portrait, Story, Cinema (see full table below)
- 🎲 **Surprise Me** — Random prompt suggestions for creative inspiration
- 📊 **Live Status Polling** — Real-time status updates ("Kaggle GPU rendering... 1m 30s elapsed")
- ☁️ **Supabase Storage** — Every generated image is automatically saved to the cloud
- ⬇️ **One-Click Download** — Download button appears after image is ready
- 🔄 **Manual Fetch** — Force-download the latest kernel output at any time
- 🛡️ **CORS-Secured** — Backend configured to only accept requests from your Vercel domain
- 🔧 **Auto Size Injection** — Selected canvas ratio is automatically written into the Kaggle script at runtime
- 🔁 **Retry Logic** — Download retries 3 times before reporting failure
- 🕐 **15-Minute Timeout** — Hard cap prevents infinite polling

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, TailwindCSS, Vanilla JS | Studio UI served from Design/index.html |
| **Backend** | Python 3.10+, Flask | REST API, pipeline orchestration, Supabase proxy |
| **AI Model** | DreamShaper XL v2 Turbo (SDXL) | Text-to-image generation |
| **GPU Runtime** | Kaggle Kernels (free T4/P100) | Where the actual AI computation happens |
| **Image Storage** | Supabase Storage | Persistent bucket for all generated PNGs |
| **Prompt Injection** | Kaggle CLI + Python file manipulation | Writes user prompt into Kaggle/kaggle.py before push |
| **Frontend Hosting** | Vercel | Serves the static HTML frontend |
| **Backend Hosting** | Railway | Runs the Flask server 24/7 |

---

## 🏗 Project Architecture

`
+------------------------------------------------------------------+
|                         USER BROWSER                             |
|              Design/index.html (Vercel / Flask)                  |
|   [Prompt Input] [Aspect Ratio] [Generate] [Fetch] [Download]    |
+-------------------------+----------------------------------------+
                          | POST /generate
                          v
+------------------------------------------------------------------+
|              FLASK BACKEND (main.py) - Railway                   |
|                                                                  |
|  1. Saves prompt to Prompt/prompt.json                           |
|  2. Runs Prompt/prompt.py => injects prompt into Kaggle/kaggle.py|
|  3. Injects canvas size (width/height) into Kaggle/kaggle.py     |
|  4. Runs Kaggle/trigger.py => pushes & triggers Kaggle kernel    |
|  5. Polls Kaggle CLI for kernel status (every 15 seconds)        |
|  6. On complete => downloads output PNG via kaggle CLI           |
|  7. Uploads PNG to Supabase Storage                              |
|  8. Returns image URL to browser via /status                     |
+------------------+------------------------+---------------------+
                   |                        |
                   v                        v
+---------------------------+   +----------------------------------+
|   KAGGLE KERNEL (GPU)     |   |     SUPABASE STORAGE             |
|   Kaggle/kaggle.py        |   |     Bucket: "Img Store"          |
|   Model: DreamShaper XL   |   |     generated_<timestamp>.png    |
|   Free Tesla T4 GPU       |   |     Auto-served via /image/<n>   |
|   ~1-4 min per image      |   |                                  |
+---------------------------+   +----------------------------------+
`

---

## 📁 Folder Structure

`
AI-Img-Generator/
|
|-- main.py                      # Flask backend server (main entry point)
|-- requirements.txt             # Python dependencies
|-- .env                         # Secret keys (NEVER commit this!)
|-- .gitignore                   # Ignores .env
|-- fix_layout.py                # One-time patch: fixes image layout in index.html
|-- patch_index.py               # One-time patch: adds Download button to index.html
|
|-- Design/                      # Frontend (web UI)
|   |-- index.html               # Main UI — the Studio AI interface
|   |-- index.html.bak           # Auto-backup before patch_index.py runs
|   |-- index.html.bak2          # Auto-backup before fix_layout.py runs
|   |-- vercel.json              # Vercel deployment config for the frontend
|   +-- output/                  # Local cache of downloaded images (auto-created)
|
|-- Prompt/                      # Prompt management
|   |-- prompt.json              # Active prompt + selected size (auto-written by backend)
|   +-- prompt.py                # Injects prompt from prompt.json into Kaggle/kaggle.py
|
+-- Kaggle/                      # Kaggle GPU pipeline
    |-- kaggle.py                # The script that runs ON Kaggle (SD XL model)
    |-- trigger.py               # Pushes kaggle.py to Kaggle and triggers execution
    |-- store.py                 # Standalone: download output + upload to Supabase
    |-- kernel-metadata.json     # Kaggle kernel config (ID, GPU, internet settings)
    +-- downloaded_output/       # Temp folder for downloaded kernel outputs
`

### File Descriptions

| File | Role |
|---|---|
| **main.py** | The heart of the project. Flask web server with all API routes, pipeline orchestration, Supabase client, Kaggle CLI wrappers, and background threading. |
| **Prompt/prompt.py** | Reads the user prompt from prompt.json and injects it into Kaggle/kaggle.py between the PROMPT_START/PROMPT_END markers. |
| **Prompt/prompt.json** | Auto-written by the backend when user clicks Generate. Stores the current prompt, width, height, and ratio name. |
| **Kaggle/kaggle.py** | The script that actually RUNS on Kaggle's GPU. Loads DreamShaper XL, generates the image, resizes it, zips it. |
| **Kaggle/trigger.py** | Calls kaggle kernels push -p Kaggle to upload the updated script and trigger a new GPU run. |
| **Kaggle/store.py** | Standalone alternative to the automatic pipeline. Manually polls Kaggle, downloads output, uploads to Supabase. |
| **Kaggle/kernel-metadata.json** | Tells the Kaggle CLI what kernel to push to (ID, GPU enabled, internet enabled). |
| **Design/index.html** | The entire frontend UI — dark studio design, prompt textarea, aspect ratio buttons, canvas, status updates. |
| **Design/vercel.json** | Vercel config — rewrites all routes to index.html and sets security headers. |
| **patch_index.py** | One-time script that patches index.html to add a Download button. |
| **fix_layout.py** | One-time script that patches index.html to fix image canvas layout. |

---

## 🔄 How the Pipeline Works

### Step-by-Step Flow (Server Side)

`
User clicks "Generate" in browser
         |
         v
POST /generate (Flask) receives { prompt, ratio }
         |
         |-- 1. Writes Prompt/prompt.json with prompt + size
         |
         |-- 2. Runs: python Prompt/prompt.py
         |        Reads prompt.json
         |        Finds <<PROMPT_START>> marker in Kaggle/kaggle.py
         |        Replaces CURRENT_PROMPT = "..." with user's text
         |
         |-- 3. inject_size(width, height)
         |        Finds <<SIZE_START>> marker in Kaggle/kaggle.py
         |        Writes: TARGET_WIDTH = 1920 / TARGET_HEIGHT = 1080
         |
         |-- 4. Runs: python Kaggle/trigger.py
         |        Executes: kaggle kernels push -p Kaggle
         |        Kaggle receives updated kaggle.py
         |        New GPU job is queued
         |
         +-- 5. Background thread: poll_then_download()
                  Every 15s: kaggle kernels status <kernel-id>
                  Waits for status = "complete"
                  kaggle kernels output => downloads ZIP
                  Extracts PNG from ZIP
                  fit_to_size() center-crops to exact ratio
                  Uploads PNG to Supabase bucket
                  Sets gen_state["image"] = "/image/<name>"

Browser polls GET /status every 3 seconds
         When status == "done" => shows image in canvas
`

### What Runs on Kaggle (kaggle.py)

`
kaggle.py runs on Kaggle GPU
         |
         |-- Reads CURRENT_PROMPT (injected by prompt.py)
         |-- Reads TARGET_WIDTH / TARGET_HEIGHT (injected by main.py)
         |-- Calculates optimal generation size (~1MP, preserves ratio)
         |-- Loads DreamShaper XL Turbo from HuggingFace
         |-- Generates image: 6 inference steps, guidance_scale=2.0
         |-- Resizes to exact target dimensions using LANCZOS
         |-- Saves: /kaggle/working/images/generated_img.png
         +-- Zips output: /kaggle/working/generated_images.zip
`

---

## 💻 Installation and Local Setup

### Prerequisites

- Python 3.10 or higher
- A [Kaggle account](https://kaggle.com) with API key
- A [Supabase account](https://supabase.com) (free tier works)
- Kaggle CLI configured

### 1. Clone the Repository

`ash
git clone https://github.com/YOUR_USERNAME/AI-Img-Generator.git
cd AI-Img-Generator
`

### 2. Create a Virtual Environment

`ash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
`

### 3. Install Dependencies

`ash
pip install -r requirements.txt
`

**What gets installed:**

| Package | Purpose |
|---|---|
| flask | Web server / REST API |
| flask-cors | Cross-Origin Resource Sharing for Vercel frontend |
| gunicorn | Production WSGI server (used on Railway) |
| python-dotenv | Loads .env variables |
| kaggle | Kaggle CLI — push kernels, poll status, download output |
| supabase | Supabase Python client for Storage |
| pillow | Image processing (resize, crop, validate) |

### 4. Set Up Environment Variables

Create a .env file in the project root:

`env
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
SUPABASE_BUCKET=Img Store
`

> **WARNING: NEVER commit .env to Git.** It is already listed in .gitignore.

### 5. Apply UI Patches (Run Once)

These scripts fix the frontend layout. Run them once after cloning:

`ash
# Step 1: Adds Download Image button to the UI
python patch_index.py

# Step 2: Fixes image display layout
python fix_layout.py
`

These are safe — they back up index.html before patching.

### 6. Run the Server Locally

`ash
python main.py
`

Open your browser at: **http://localhost:5000**

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| KAGGLE_USERNAME | Yes | Your Kaggle username |
| KAGGLE_KEY | Yes | Your Kaggle API key |
| SUPABASE_URL | Yes | Your Supabase project URL |
| SUPABASE_KEY | Yes | Supabase **service role** key (NOT the anon key!) |
| SUPABASE_BUCKET | Optional | Storage bucket name (default: Img Store) |

> **Why service role key?** The anon key is blocked by Row Level Security (RLS) for uploads. The service role key bypasses RLS and is required for server-side storage operations.

---

## 🏁 Kaggle Setup

### Step 1: Create a Kaggle Account

Go to [kaggle.com](https://kaggle.com) and sign up (completely free).

### Step 2: Get Your API Key

1. Go to **Account Settings → API → Create New Token**
2. Download kaggle.json
3. Copy the username and key values into your .env file

### Step 3: Create a Kaggle Kernel

1. Go to [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook**
2. Name it exactly: **img-generator** (must match kernel-metadata.json)
3. Enable **GPU** accelerator in kernel settings
4. Enable **Internet** access in kernel settings
5. Save and run it once manually to create the kernel slot

### Step 4: Update kernel-metadata.json

Edit Kaggle/kernel-metadata.json to match your Kaggle username:

`json
{
  "id": "YOUR_KAGGLE_USERNAME/img-generator",
  "title": "Img Generator",
  "code_file": "kaggle.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": []
}
`

### Step 5: Verify Kaggle CLI Works

`ash
kaggle kernels list --mine
`

You should see your img-generator kernel listed.

---

## 🗄 Supabase Setup

### Step 1: Create a Project

1. Go to [supabase.com](https://supabase.com) and create a new project (free tier)
2. Go to **Settings → API** and copy:
   - **Project URL** → SUPABASE_URL in .env
   - **service_role secret** → SUPABASE_KEY in .env

### Step 2: Create a Storage Bucket

1. In Supabase dashboard → **Storage** → **New Bucket**
2. Name it: **Img Store** (or anything — update SUPABASE_BUCKET in .env)
3. Set visibility to **Public** (required for images to display in browser)

### Step 3: Configure RLS Policies (if needed)

If you use the service_role key, RLS is bypassed automatically. If you want to add public read access via SQL:

`sql
-- Allow public read access to images
CREATE POLICY "Public Read" ON storage.objects
  FOR SELECT USING (bucket_id = 'Img Store');

-- Allow server-side uploads
CREATE POLICY "Auth Upload" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'Img Store');
`

---

## 🚀 Deployment Guide

### Deploy Frontend to Vercel

The Design/ folder contains the static frontend with index.html and vercel.json.

#### Step 1: Push Code to GitHub

`ash
git add .
git commit -m "Initial commit"
git push origin main
`

#### Step 2: Import to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repository
3. **IMPORTANT — Root Directory:** Set to Design
4. **Framework Preset:** Other (not Next.js or anything else)
5. Click **Deploy**

#### Step 3: vercel.json Explained

The Design/vercel.json is already configured — no changes needed:

`json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ]
}
`

- **rewrites**: All URLs serve index.html (SPA behavior)
- **headers**: Security headers added automatically on every response

#### Step 4: Point Frontend at Your Backend

In Design/index.html, update the API base URL to point to your Railway backend:

`javascript
const API_BASE = "https://your-backend.railway.app";
`

#### What Vercel Provides
- Free HTTPS certificate
- Global CDN (fast loading worldwide)
- Automatic deploys on every Git push
- Preview URLs for every pull request

---

### Deploy Backend to Railway

Railway runs the Flask backend (main.py) continuously in the cloud.

#### Step 1: Create a Railway Account

Go to [railway.app](https://railway.app) and sign up. Free tier includes /month credit.

#### Step 2: Create New Project from GitHub

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Choose your AI-Img-Generator repository
4. Railway auto-detects Python via requirements.txt

#### Step 3: Add Environment Variables

In Railway dashboard → your service → **Variables** tab, add all secrets:

`
KAGGLE_USERNAME   =  your_kaggle_username
KAGGLE_KEY        =  your_kaggle_api_key
SUPABASE_URL      =  https://yourproject.supabase.co
SUPABASE_KEY      =  your_service_role_key
SUPABASE_BUCKET   =  Img Store
`

#### Step 4: Create a Procfile

Create a file named Procfile in the project root (no extension):

`
web: gunicorn main:app --bind 0.0.0.0: --workers 1 --timeout 120
`

Or set the Start Command in Railway Settings → Deploy:

`
gunicorn main:app --bind 0.0.0.0: --workers 1 --timeout 120
`

> **Note:** Use --workers 1 because the pipeline stores state in memory (gen_state dict). Multiple workers would lose state between requests.

#### Step 5: Kaggle CLI on Railway

The Kaggle Python package is installed from requirements.txt. It automatically reads KAGGLE_USERNAME and KAGGLE_KEY from environment variables — no kaggle.json file needed on Railway.

#### Step 6: Add Vercel Domain to CORS

In main.py, add your Vercel URL to the allowed origins:

`python
CORS(app, origins=[
    "https://your-project.vercel.app",      # <-- Add your URL
    "https://ai-img-generator-beta.vercel.app",
    r"https://.*\.vercel\.app",
    "http://localhost:5000",
])
`

Re-deploy after this change.

#### Step 7: Get Your Railway Public URL

In Railway dashboard → your service → **Settings → Networking** → Generate Domain.

You'll get something like: https://ai-img-generator-production.up.railway.app

Update this URL in your Design/index.html frontend.

#### What Railway Does
- Keeps Flask running 24/7
- Handles all API calls: /generate, /status, /image/*, /download/*
- Runs Kaggle polling in background threads
- Proxies images from Supabase to the browser

---

## 📡 API Reference

All endpoints are in main.py (Flask).

| Method | Endpoint | Description |
|---|---|---|
| GET | / | Serves the Studio AI frontend (index.html) |
| POST | /generate | Starts the image generation pipeline |
| GET | /status | Returns current pipeline state (browser polls this) |
| GET | /surprise | Returns a random creative prompt string |
| GET | /last-image | Returns the URL of the most recently generated image |
| POST | /fetch-now | Force-downloads the latest Kaggle output immediately |
| POST | /reset | Resets the pipeline state back to idle |
| GET | /image/<name> | Proxies image from Supabase (or local fallback) |
| GET | /download/<name> | Sends image as a file attachment (triggers download) |
| GET | /output/<filename> | Serves locally cached image files |

### POST /generate — Request Body

`json
{
  "prompt": "A futuristic floating city above the clouds at golden hour",
  "ratio": "16:9 Wide"
}
`

### GET /status — Response Format

`json
{
  "status": "waiting",
  "message": "Kaggle GPU rendering... 1m 30s elapsed",
  "image": null
}
`

**Status Values:**

| Status | Meaning |
|---|---|
| idle | Ready — no job running |
| running | Injecting prompt and pushing to Kaggle |
| waiting | Polling Kaggle for kernel completion |
| done | Image is ready, URL is in the "image" field |
| error | Something went wrong — details in "message" |

---

## 📐 Supported Aspect Ratios

| Button Name | Pixel Dimensions | Best Use Case |
|---|---|---|
| 1:1 Square | 1024 × 1024 px | Instagram posts, profile pictures, thumbnails |
| 16:9 Wide | 1920 × 1080 px | YouTube thumbnails, desktop wallpapers, presentations |
| 4:3 Classic | 1440 × 1080 px | Photography, blog headers, classic displays |
| 3:4 Portrait | 1080 × 1440 px | Pinterest pins, portrait photography |
| 9:16 Story | 1080 × 1920 px | Instagram Stories, TikTok, YouTube Shorts |
| 21:9 Cinema | 2560 × 1080 px | Ultra-wide wallpapers, cinematic banner art |

**Smart Sizing System:** The backend does NOT send the full resolution to Kaggle for generation. Instead it:
1. Calculates an optimal ~1-megapixel generation size (SDXL's sweet spot)
2. Preserves the exact aspect ratio of your chosen preset
3. Generates at the optimal size for quality
4. Resizes the result to the full target resolution using LANCZOS resampling
5. Falls back to center-cropping if Kaggle returns a different size

---

## 🔧 Utility Scripts

### patch_index.py

Adds a **Download Image** button below the generated image canvas in the UI.

`ash
python patch_index.py
`

- Run once after cloning
- Creates a backup at Design/index.html.bak
- Idempotent — running twice does nothing (checks if already patched)

### fix_layout.py

Ensures the generated image canvas is always fully visible and moves the Download button into the bottom toolbar.

`ash
python fix_layout.py
`

- Run once (after patch_index.py)
- Creates a backup at Design/index.html.bak2
- Idempotent — prints "already fixed" if run again

### Kaggle/store.py

A **standalone alternative pipeline** for manually downloading Kaggle output and uploading to Supabase. Useful for:
- Debugging when the automatic pipeline fails
- Downloading images from runs triggered manually on the Kaggle website
- Running as a separate scheduled job

`ash
python Kaggle/store.py
`

This script:
1. Authenticates with the Kaggle API directly
2. Reads the kernel ID from kernel-metadata.json
3. Polls until the kernel completes (every 15 seconds, up to 30 minutes)
4. Downloads all image files from the kernel output
5. Uploads each image to your Supabase bucket with a timestamp prefix

---

## ❓ Troubleshooting

### "Kaggle kernel reported an error"

**Cause:** The Kaggle script failed during execution.

**Fix:**
1. Open [kaggle.com/code](https://kaggle.com/code)
2. Click your img-generator kernel
3. Check the execution logs for the error
4. Most common cause: internet not enabled → make sure "enable_internet": true in kernel-metadata.json

---

### "Timed out (15 min)"

**Cause:** The Kaggle free GPU queue was very busy, or the kernel took too long.

**Fix:**
1. Click the **Fetch Image** button — if the kernel actually finished, it will download the image
2. Check [kaggle.com/code](https://kaggle.com/code) directly to see the kernel status
3. If it finished, run: python Kaggle/store.py to download manually

---

### "SUPABASE_URL / SUPABASE_KEY missing in .env"

**Cause:** The .env file is not found or has wrong content.

**Fix:**
- Check that .env is in the project root (same folder as main.py)
- Make sure you used the **service_role** key from Supabase, NOT the anon key
- On Railway, check that the Variables tab has all required keys

---

### "Could not find PROMPT_START marker"

**Cause:** The Kaggle/kaggle.py file was manually edited and the injection markers were deleted.

**Fix:** Restore the markers manually at the top of Kaggle/kaggle.py:

`python
# <<PROMPT_START>> auto-injected by Prompt/prompt.py - do not edit manually
CURRENT_PROMPT = """your test prompt here"""
# <<PROMPT_END>>

# <<SIZE_START>> auto-injected by app.py - do not edit manually
TARGET_WIDTH = 1024
TARGET_HEIGHT = 1024
# <<SIZE_END>>
`

---

### CORS errors in browser console

**Cause:** The Flask backend is rejecting requests from the frontend domain.

**Fix:**
1. In main.py, add your exact Vercel URL to the CORS origins list
2. Redeploy the backend on Railway

---

### Image shows as broken / fails to load

**Cause:** Kaggle returned an image with a different size than requested, and the resize failed.

**Fix:**
- Check the backend logs for [WARN] or [FIT ERROR] messages
- The fit_to_size() function in main.py auto-corrects this — it should still save a valid image
- If the Supabase upload failed, the image is served from the local /output/ folder as fallback

---

### "kaggle: command not found" on Railway

**Cause:** Kaggle CLI is not installed.

**Fix:**
- The kaggle package is in requirements.txt and should install automatically
- Railway uses KAGGLE_USERNAME and KAGGLE_KEY env vars — no kaggle.json file needed

---

## 🤝 Contributing

Pull requests are welcome! Here is how to contribute:

1. Fork the repository
2. Create your feature branch: git checkout -b feature/amazing-feature
3. Make your changes and test locally: python main.py
4. Commit: git commit -m "Add amazing feature"
5. Push: git push origin feature/amazing-feature
6. Open a Pull Request

### Ideas for Future Contributions

- [ ] Add negative prompt support (the UI button exists — backend not yet wired)
- [ ] Support multiple images per generation (batch mode)
- [ ] Add image history gallery page using Supabase list API
- [ ] Support additional models: FLUX.1, SDXL Lightning, Stable Cascade
- [ ] Add generation parameter controls (steps, guidance scale, seed)
- [ ] Mobile-responsive layout for the Studio UI
- [ ] Add user authentication so multiple users can use it simultaneously

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**Made with free Kaggle GPUs**

If this project helped you, please star the repo!

</div>
