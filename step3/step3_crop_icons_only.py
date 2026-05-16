"""Standalone Step 3: crop icon regions from boxlib.json.

Outputs:
- icons/icon_AF01.png, icon_AF02.png, ...
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


# ---- Hardcoded configuration ----
IMAGE_PATH = "step2/sample_images/Validation_Framework_Medical_Vision_202605151644.jpeg"
BOXLIB_PATH = f"step2/sam3_outputs/{Path(IMAGE_PATH).stem}/boxlib.json"
OUTPUT_DIR = f"step3/icons_output/{Path(IMAGE_PATH).stem}"


def _label_to_filename(label: str, fallback_id: int) -> str:
    if label:
        clean = label.replace("<", "").replace(">", "")
        return f"icon_{clean}.png"
    return f"icon_AF{fallback_id + 1:02d}.png"


def run() -> None:
    image_path = Path(IMAGE_PATH)
    boxlib_path = Path(BOXLIB_PATH)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not boxlib_path.is_file():
        raise FileNotFoundError(f"Boxlib not found: {boxlib_path}")

    with Image.open(str(image_path)) as image:
        with boxlib_path.open("r", encoding="utf-8") as f:
            boxlib = json.load(f)

        boxes = boxlib.get("boxes", [])
        if not boxes:
            print("No boxes found; nothing to crop.")
            return

        for idx, box in enumerate(boxes):
            x1 = int(box.get("x1", 0))
            y1 = int(box.get("y1", 0))
            x2 = int(box.get("x2", 0))
            y2 = int(box.get("y2", 0))

            if x2 <= x1 or y2 <= y1:
                print(f"Skip invalid box #{idx}: ({x1}, {y1}, {x2}, {y2})")
                continue

            label = str(box.get("label", ""))
            filename = _label_to_filename(label, idx)
            output_path = output_dir / filename

            cropped = image.crop((x1, y1, x2, y2))
            cropped.save(str(output_path))
            print(f"Saved: {output_path}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
