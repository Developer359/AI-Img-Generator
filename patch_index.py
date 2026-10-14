"""
Run once from the project root:   python patch_index.py

Patches Design/index.html:
  1. adds a "Download Image" button below the generated image
  2. fixes showImage() so the image URL is not broken by the cache-buster
  3. shows a message if the image fails to load
A backup is saved as Design/index.html.bak
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "Design", "index.html")

NEW_WRAP = '''<div id="canvas-image-wrap" style="display:none;width:100%;height:100%;position:relative;flex-direction:column;padding:14px;gap:12px;">
      <img id="canvas-image" src="" alt="Generated image"
        onerror="this.onerror=null; showPlaceholder('Image failed to load', 'Press Fetch Image to try again.', 'broken_image', false, false);"
        style="flex:1;min-height:0;width:100%;object-fit:contain;border-radius:14px;" />
      <!-- Download button (below the image) -->
      <div style="display:flex;justify-content:center;flex-shrink:0;">
        <a id="btn-download" href="#" download
          class="flex items-center space-x-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium border border-purple-400/30 shadow-lg shadow-purple-600/25 transition-all"
          style="padding:9px 20px;font-size:12px;text-decoration:none;">
          <span class="material-symbols-outlined" style="font-size:16px;">download</span>
          <span>Download Image</span>
        </a>
      </div>
    </div>'''

OLD_SRC = "img.src = src + '?t=' + Date.now();"
NEW_SRC = (
    "img.src = src + (src.includes('?') ? '&' : '?') + 't=' + Date.now();\n"
    "    const dl = document.getElementById('btn-download');\n"
    "    if (dl) dl.href = '/download/' + encodeURIComponent(src.split('?')[0].split('/').pop());"
)

OLD_DISPLAY = "wrap.style.display = 'block';"
NEW_DISPLAY = "wrap.style.display = 'flex';"


def main():
    if not os.path.isfile(PATH):
        sys.exit(f"Cannot find {PATH}")

    with open(PATH, "rb") as f:
        raw = f.read()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")

    if 'id="btn-download"' in text:
        sys.exit("index.html is already patched. Nothing to do.")

    shutil.copyfile(PATH, PATH + ".bak")

    text, n1 = re.subn(r'<div id="canvas-image-wrap".*?</div>', lambda m: NEW_WRAP,
                       text, count=1, flags=re.S)
    if OLD_SRC not in text or OLD_DISPLAY not in text:
        sys.exit("Could not find the showImage() lines. Your index.html is different "
                 "from the one I saw. Send it to me and I will adjust the patch.")
    text = text.replace(OLD_SRC, NEW_SRC, 1)
    text = text.replace(OLD_DISPLAY, NEW_DISPLAY, 1)

    if n1 != 1:
        sys.exit("Could not find the image wrapper in index.html.")

    if crlf:
        text = text.replace("\n", "\r\n")
    with open(PATH, "wb") as f:
        f.write((b"\xef\xbb\xbf" if has_bom else b"") + text.encode("utf-8"))

    print("Done. index.html patched (backup: Design/index.html.bak).")


if __name__ == "__main__":
    main()