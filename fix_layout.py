"""
Run once from the project root:   python fix_layout.py

Patches Design/index.html:
  1. the generated image is always fully visible (never cut, never under the toolbar)
  2. the Download button moves into the bottom toolbar, right next to "Fetch Image"
Works whether or not patch_index.py was run before. Backup: Design/index.html.bak2
"""

import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "Design", "index.html")

NEW_WRAP = '''<div id="canvas-image-wrap" style="display:none;position:absolute;inset:0;flex-direction:column;padding:16px 16px 66px 16px;">
      <img id="canvas-image" src="" alt="Generated image"
        onerror="this.onerror=null; showPlaceholder('Image failed to load', 'Press Fetch Image to try again.', 'broken_image', false, false);"
        style="flex:1;min-height:0;width:100%;object-fit:contain;border-radius:14px;" />
    </div>
'''

DOWNLOAD_BTN = '''
      <span style="color:rgb(51,65,85);">|</span>
      <!-- Download button: saves the current image -->
      <a id="btn-download" data-toolbar-download href="#" download class="flex items-center space-x-1 px-2 py-0.5 rounded hover:bg-purple-500/20 hover:text-purple-300 transition" title="Download this image" style="font-size:10px;color:rgb(168,85,247);opacity:0.4;pointer-events:none;text-decoration:none;">
        <span class="material-symbols-outlined" style="font-size:13px;">file_download</span>
        <span>Download</span>
      </a>'''

NEW_SHOW_IMAGE = '''function showImage(src) {
    document.getElementById('canvas-placeholder').style.display = 'none';
    const wrap = document.getElementById('canvas-image-wrap');
    const img  = document.getElementById('canvas-image');
    img.src = src + (src.includes('?') ? '&' : '?') + 't=' + Date.now();
    const dl = document.getElementById('btn-download');
    if (dl) {
      dl.href = '/download/' + encodeURIComponent(src.split('?')[0].split('/').pop());
      dl.style.opacity = '1';
      dl.style.pointerEvents = 'auto';
    }
    wrap.style.display = 'flex';
  }
'''

HIDE_LINE = "document.getElementById('canvas-image-wrap').style.display = 'none';"
HIDE_NEW = (HIDE_LINE + "\n"
            "    const dlBtn = document.getElementById('btn-download');\n"
            "    if (dlBtn) { dlBtn.style.opacity = '0.4'; dlBtn.style.pointerEvents = 'none'; dlBtn.href = '#'; }")


def main():
    if not os.path.isfile(PATH):
        sys.exit(f"Cannot find {PATH}")

    with open(PATH, "rb") as f:
        raw = f.read()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")

    if "data-toolbar-download" in text:
        sys.exit("Layout is already fixed. Nothing to do. (Press Ctrl+F5 in the browser.)")

    shutil.copyfile(PATH, PATH + ".bak2")

    # 1. image wrapper (everything from the wrapper up to the toolbar comment)
    text, n = re.subn(r'<div id="canvas-image-wrap".*?(?=\s*<!-- Bottom toolbar -->)',
                      lambda m: NEW_WRAP.rstrip("\n"), text, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find the image wrapper / toolbar comment in index.html.")

    # 2. showImage()
    text, n = re.subn(r"function showImage\(src\) \{.*?\n  \}\n", lambda m: NEW_SHOW_IMAGE,
                      text, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find showImage() in index.html.")

    # 3. showPlaceholder(): disable Download while no image is shown
    if HIDE_LINE not in text:
        sys.exit("Could not find showPlaceholder() in index.html.")
    text = text.replace(HIDE_LINE, HIDE_NEW, 1)

    # 4. Download button in the toolbar, right after "Fetch Image"
    text, n = re.subn(r"(<span>Fetch Image</span>\s*</button>)",
                      lambda m: m.group(1) + DOWNLOAD_BTN, text, count=1)
    if n != 1:
        sys.exit("Could not find the Fetch Image button in index.html.")

    if crlf:
        text = text.replace("\n", "\r\n")
    with open(PATH, "wb") as f:
        f.write((b"\xef\xbb\xbf" if has_bom else b"") + text.encode("utf-8"))

    print("Done. index.html fixed (backup: Design/index.html.bak2).")
    print("Now press Ctrl+F5 in the browser.")


if __name__ == "__main__":
    main()