import os
import json

if __name__ == "__main__":
    # Resolve paths — works from any directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)  # one level up from Prompt/

    # Load prompt from Prompt/prompt.json (same folder as this script)
    json_path = os.path.join(base_dir, "prompt.json")
    if not os.path.exists(json_path):
        # Fallback: check project root
        json_path = os.path.join(root_dir, "prompt.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"prompt.json not found! Expected at: {os.path.join(base_dir, 'prompt.json')}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    manual_prompt = data.get("prompt", "").strip()
    if not manual_prompt:
        raise ValueError("The 'prompt' field in prompt.json is empty!")

    print(f"Loaded prompt:\n-> {manual_prompt}")

    # Inject prompt directly into Kaggle/kaggle.py (between special markers)
    kaggle_script = os.path.join(root_dir, "Kaggle", "kaggle.py")
    if not os.path.exists(kaggle_script):
        raise FileNotFoundError(f"kaggle.py not found at: {kaggle_script}")

    with open(kaggle_script, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace the CURRENT_PROMPT line — simple line-by-line approach (works with \r\n and \n)
    lines = content.splitlines(keepends=True)
    new_lines = []
    in_block = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# <<PROMPT_START>>"):
            in_block = True
            new_lines.append(line)
        elif in_block and stripped.startswith("CURRENT_PROMPT"):
            # Preserve the original line ending
            ending = "\r\n" if line.endswith("\r\n") else "\n"
            new_lines.append(f'CURRENT_PROMPT = """{manual_prompt}"""{ending}')
            in_block = False
            replaced = True
        else:
            new_lines.append(line)
    new_content = "".join(new_lines)

    if not replaced:
        raise RuntimeError("Could not find <<PROMPT_START>> marker or CURRENT_PROMPT line in kaggle.py!")

    with open(kaggle_script, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"SUCCESS: Prompt injected into {kaggle_script}")
    print("Now run: python Kaggle/trigger.py")