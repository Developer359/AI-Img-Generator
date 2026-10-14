"""
Kaggle/store.py
Pulls the generated image(s) from the Kaggle kernel output and uploads
them to a Supabase Storage bucket.

Required in .env (project root):
    KAGGLE_USERNAME=your_kaggle_username
    KAGGLE_KEY=your_kaggle_api_key
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=your_SERVICE_ROLE_key      # not the anon key (RLS will block uploads)

Optional in .env:
    SUPABASE_BUCKET=Img Store               # default
    KAGGLE_KERNEL=username/kernel-slug      # default: read from kernel-metadata.json

Install:
    pip install kaggle supabase python-dotenv
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")  # must run BEFORE importing kaggle

# Stop Python from importing the local Kaggle/kaggle.py instead of the pip package
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]

from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402
from supabase import create_client  # noqa: E402

DOWNLOAD_DIR = HERE / "downloaded_output"
BUCKET = os.getenv("SUPABASE_BUCKET", "Img Store")
WAIT_FOR_KERNEL = True       # wait until the Kaggle run finishes
POLL_SECONDS = 15
TIMEOUT_SECONDS = 30 * 60    # 30 min max wait
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def get_kernel_ref() -> str:
    ref = os.getenv("KAGGLE_KERNEL")
    if ref:
        return ref
    meta_path = HERE / "kernel-metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)["id"]  # e.g. "username/my-kernel"


def wait_for_kernel(api: KaggleApi, kernel: str) -> None:
    print(f"Checking Kaggle kernel status: {kernel}")
    start = time.time()
    while True:
        status = str(api.kernels_status(kernel).status).lower()
        print(f"  status -> {status}")
        if "complete" in status:
            return
        if "error" in status or "cancel" in status:
            raise RuntimeError(f"Kaggle kernel ended with status: {status}")
        if time.time() - start > TIMEOUT_SECONDS:
            raise TimeoutError("Timed out waiting for the Kaggle kernel to finish.")
        time.sleep(POLL_SECONDS)


def download_output(api: KaggleApi, kernel: str) -> list[Path]:
    if DOWNLOAD_DIR.exists():
        shutil.rmtree(DOWNLOAD_DIR)
    DOWNLOAD_DIR.mkdir(parents=True)

    print("Downloading kernel output from Kaggle...")
    api.kernels_output(kernel, path=str(DOWNLOAD_DIR), force=True, quiet=False)

    images = [
        p for p in DOWNLOAD_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    if not images:
        files = [str(p.relative_to(DOWNLOAD_DIR)) for p in DOWNLOAD_DIR.rglob("*") if p.is_file()]
        raise FileNotFoundError(
            f"No images found in Kaggle output. Files downloaded: {files or 'none'}"
        )
    print(f"Found {len(images)} image(s).")
    return images


def upload_to_supabase(images: list[Path]) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing in .env")

    supabase = create_client(url, key)
    bucket = supabase.storage.from_(BUCKET)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for img in images:
        remote_name = f"{stamp}_{img.name}"
        mime = "image/png" if img.suffix.lower() == ".png" else (
            "image/webp" if img.suffix.lower() == ".webp" else "image/jpeg"
        )
        print(f"Uploading {img.name} -> {BUCKET}/{remote_name}")
        with open(img, "rb") as f:
            bucket.upload(
                path=remote_name,
                file=f.read(),
                file_options={"content-type": mime, "upsert": "true"},
            )
        try:
            public_url = bucket.get_public_url(remote_name)
            print(f"  Done. URL: {public_url}")
        except Exception:
            print("  Done.")


def main() -> None:
    api = KaggleApi()
    api.authenticate()

    kernel = get_kernel_ref()
    if WAIT_FOR_KERNEL:
        wait_for_kernel(api, kernel)

    images = download_output(api, kernel)
    upload_to_supabase(images)
    print("All done: image stored in Supabase.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)