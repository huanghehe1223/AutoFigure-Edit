"""Standalone Step 3: RMBG-2.0 batch background removal for cropped icons.

Outputs:
- icon_AF01_nobg.png, icon_AF02_nobg.png, ...
- icon_infos.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


# ---- Hardcoded configuration ----
MODEL_DIR = "rmbg/models/RMBG-2.0"
ICONS_DIR = "step3/icons_output/Validation_Framework_Medical_Vision_202605151644"
BOXLIB_PATH = f"step2/sam3_outputs/{Path(ICONS_DIR).stem}/boxlib.json"
OUTPUT_DIR = f"step3/icon_rmbg_outputs/{Path(ICONS_DIR).stem}"
ICON_INFOS_JSON = f"{OUTPUT_DIR}/icon_infos.json"
TARGET_SIZE = (512, 512)
BATCH_SIZE = 8


def letterbox_image(
    image: Image.Image,
    target_size: Tuple[int, int],
) -> Tuple[Image.Image, Dict[str, object]]:
    target_w, target_h = target_size
    orig_w, orig_h = image.size

    scale = min(target_w / orig_w, target_h / orig_h)
    resized_w = max(1, int(round(orig_w * scale)))
    resized_h = max(1, int(round(orig_h * scale)))

    resized = image.resize((resized_w, resized_h), resample=Image.LANCZOS)
    padded = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    pad_left = (target_w - resized_w) // 2
    pad_top = (target_h - resized_h) // 2
    padded.paste(resized, (pad_left, pad_top))

    meta = {
        "pad_left": pad_left,
        "pad_top": pad_top,
        "resized_size": (resized_w, resized_h),
        "original_size": (orig_w, orig_h),
    }
    return padded, meta


def iter_batches(items: List[Path], batch_size: int) -> List[List[Path]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _label_clean(label: str, fallback_id: int) -> str:
    if label:
        return label.replace("<", "").replace(">", "")
    return f"AF{fallback_id + 1:02d}"


def run() -> None:
    model_dir = Path(MODEL_DIR)
    icons_dir = Path(ICONS_DIR)
    boxlib_path = Path(BOXLIB_PATH)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not model_dir.exists():
        raise FileNotFoundError(f"Model dir not found: {model_dir}")
    if not icons_dir.exists():
        raise FileNotFoundError(f"Icons dir not found: {icons_dir}")
    if not boxlib_path.exists():
        raise FileNotFoundError(f"Boxlib not found: {boxlib_path}")

    with boxlib_path.open("r", encoding="utf-8") as f:
        boxlib = json.load(f)

    boxes = boxlib.get("boxes", [])
    if not boxes:
        print("No boxes found in boxlib.json; nothing to process.")
        return

    icon_entries: List[dict] = []
    for idx, box in enumerate(boxes):
        label = str(box.get("label", ""))
        label_clean = _label_clean(label, idx)
        crop_path = icons_dir / f"icon_{label_clean}.png"
        if not crop_path.exists():
            print(f"Missing crop for box #{idx}: {crop_path}")
            continue
        icon_entries.append(
            {
                "box": box,
                "label": label,
                "label_clean": label_clean,
                "crop_path": crop_path,
            }
        )

    if not icon_entries:
        print("No cropped icons found to process.")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Model: {model_dir}")
    print(f"Icons: {len(icon_entries)}")

    model = AutoModelForImageSegmentation.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
    ).eval().to(device)

    transform_image = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    icon_infos = []

    for batch in iter_batches(icon_entries, BATCH_SIZE):
        originals: List[Image.Image] = []
        metas: List[Dict[str, object]] = []
        tensors: List[torch.Tensor] = []

        for entry in batch:
            image = Image.open(entry["crop_path"]).convert("RGB")
            padded, meta = letterbox_image(image, TARGET_SIZE)
            tensor = transform_image(padded)

            originals.append(image)
            metas.append(meta)
            tensors.append(tensor)

        batch_tensor = torch.stack(tensors).to(device)
        with torch.no_grad():
            pred = model(batch_tensor)[-1].sigmoid().cpu()

        for idx, entry in enumerate(batch):
            mask = pred[idx].squeeze(0)
            mask_pil = transforms.ToPILImage()(mask)

            pad_left = int(metas[idx]["pad_left"])
            pad_top = int(metas[idx]["pad_top"])
            resized_w, resized_h = metas[idx]["resized_size"]
            orig_w, orig_h = metas[idx]["original_size"]

            mask_pil = mask_pil.crop((pad_left, pad_top, pad_left + resized_w, pad_top + resized_h))
            mask_pil = mask_pil.resize((orig_w, orig_h), resample=Image.BILINEAR)

            output = originals[idx].copy()
            output.putalpha(mask_pil)

            label_clean = entry["label_clean"]
            output_path = output_dir / f"icon_{label_clean}_nobg.png"
            output.save(output_path)

            box = entry["box"]
            box_id = int(box.get("id", idx))
            x1 = int(box.get("x1", 0))
            y1 = int(box.get("y1", 0))
            x2 = int(box.get("x2", 0))
            y2 = int(box.get("y2", 0))

            icon_infos.append(
                {
                    "id": box_id,
                    "label": entry["label"],
                    "label_clean": label_clean,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "crop_path": str(entry["crop_path"]),
                    "nobg_path": str(output_path),
                    "original_size": [orig_w, orig_h],
                    "resized_size": [int(resized_w), int(resized_h)],
                    "pad_left": pad_left,
                    "pad_top": pad_top,
                }
            )

            print(f"Saved: {output_path}")

    with open(ICON_INFOS_JSON, "w", encoding="utf-8") as f:
        json.dump(icon_infos, f, indent=2, ensure_ascii=False)
    print(f"Saved: {ICON_INFOS_JSON}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
