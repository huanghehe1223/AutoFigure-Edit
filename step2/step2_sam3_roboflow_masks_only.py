"""Standalone Step 2: SAM3 mask visualization via Roboflow.

Outputs:
- overlay.png: original image with per-prompt masks in different colors
- crops/: each mask cropped as a transparent PNG
"""

from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw


# ---- Hardcoded configuration ----
IMAGE_PATH = "step2/sample_images/image.png"
OUTPUT_DIR = f"step2/sam3_masks_outputs/{Path(IMAGE_PATH).stem}"
TEXT_PROMPTS = "chest x-ray image,lock icon,neural network icon,gear icon,icon"
MIN_SCORE = 0.5

SAM3_ROBOFLOW_API_URL = os.environ.get(
    "ROBOFLOW_API_URL",
    "https://serverless.roboflow.com/sam3/concept_segment",
)
SAM3_API_TIMEOUT = 300

MASK_ALPHA = 120
OUTLINE_ALPHA = 220
OUTLINE_WIDTH = 2

COLOR_PALETTE = [
    (239, 83, 80),
    (102, 187, 106),
    (66, 165, 245),
    (255, 167, 38),
    (171, 71, 188),
    (38, 198, 218),
    (141, 110, 99),
    (255, 112, 67),
]


def _get_roboflow_api_key() -> str:
    return "vJfqq4sPfI9zN2gAcAOe"
    key = os.environ.get("ROBOFLOW_API_KEY") or os.environ.get("API_KEY")
    if not key:
        raise ValueError("Missing ROBOFLOW_API_KEY (or API_KEY) in environment.")
    return key


def _image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _sanitize_label(text: str) -> str:
    cleaned = []
    for ch in text:
        if ch.isalnum() or ch in ("_", "-"):
            cleaned.append(ch)
        elif ch.isspace():
            cleaned.append("_")
    return "".join(cleaned) or "prompt"


def _clamp_point(x: float, y: float, width: int, height: int) -> tuple[int, int]:
    xi = max(0, min(width - 1, int(round(x))))
    yi = max(0, min(height - 1, int(round(y))))
    return xi, yi


def _normalize_mask_points(mask: list, width: int, height: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []

    if isinstance(mask, list) and mask:
        if isinstance(mask[0], (list, tuple)) and len(mask[0]) >= 2 and isinstance(mask[0][0], (int, float)):
            for pt in mask:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    points.append(_clamp_point(pt[0], pt[1], width, height))
        else:
            for sub in mask:
                if isinstance(sub, (list, tuple)) and len(sub) >= 2 and isinstance(sub[0], (int, float)):
                    points.append(_clamp_point(sub[0], sub[1], width, height))
                elif isinstance(sub, (list, tuple)) and sub and isinstance(sub[0], (list, tuple)):
                    for pt in sub:
                        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            points.append(_clamp_point(pt[0], pt[1], width, height))

    return points


def _iter_masks_from_response(response_json: dict, width: int, height: int) -> list[list[tuple[int, int]]]:
    masks_out: list[list[tuple[int, int]]] = []

    prompt_results = response_json.get("prompt_results") if isinstance(response_json, dict) else None
    if not isinstance(prompt_results, list):
        return masks_out

    for prompt_result in prompt_results:
        if not isinstance(prompt_result, dict):
            continue
        predictions = prompt_result.get("predictions", [])
        if not isinstance(predictions, list):
            continue
        for prediction in predictions:
            if not isinstance(prediction, dict):
                continue
            confidence = prediction.get("confidence")
            score_val = float(confidence) if confidence is not None else 0.0
            if score_val < MIN_SCORE:
                continue
            masks = prediction.get("masks", [])
            if not isinstance(masks, list):
                continue
            for mask in masks:
                points = _normalize_mask_points(mask, width, height)
                if len(points) >= 3:
                    masks_out.append(points)

    return masks_out


def _call_sam3_roboflow_api(
    image_base64: str,
    prompt: str,
    api_key: str,
    min_score: float,
) -> dict:
    payload = {
        "image": {"type": "base64", "value": image_base64},
        "prompts": [{"type": "text", "text": prompt}],
        "format": "polygon",
        "output_prob_thresh": min_score,
    }

    retry_count = max(1, int(os.environ.get("SAM3_API_RETRIES", "3")))
    retry_delay = max(0.0, float(os.environ.get("SAM3_API_RETRY_DELAY", "1.5")))

    last_error: Optional[Exception] = None
    url = f"{SAM3_ROBOFLOW_API_URL}?api_key={api_key}"

    for attempt in range(1, retry_count + 1):
        try:
            response = requests.post(url, json=payload, timeout=SAM3_API_TIMEOUT)
            if response.status_code != 200:
                raise RuntimeError(f"Roboflow API error: {response.status_code} - {response.text[:500]}")
            result = response.json()
            if isinstance(result, dict) and "error" in result:
                raise RuntimeError(f"Roboflow API error: {result.get('error')}")
            return result
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                sleep_s = retry_delay * (2 ** (attempt - 1))
                print(f"Roboflow request failed ({attempt}/{retry_count}): {exc}. Retry in {sleep_s:.1f}s")
                time.sleep(sleep_s)
                continue
            break

    if last_error is not None:
        raise last_error
    raise RuntimeError("Roboflow request failed: unknown error")


def run() -> None:
    image_path = Path(IMAGE_PATH)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    output_dir = Path(OUTPUT_DIR)
    crops_dir = output_dir / "crops"
    output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    original = Image.open(str(image_path)).convert("RGBA")
    width, height = original.size

    prompt_list = [p.strip() for p in TEXT_PROMPTS.split(",") if p.strip()]
    print(f"Image: {image_path}")
    print(f"Image size: {width} x {height}")
    print(f"Prompts: {prompt_list}")

    api_key = _get_roboflow_api_key()
    image_base64 = _image_to_base64(original)

    overlay = Image.new("RGBA", original.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")

    mask_index = 0

    for prompt_idx, prompt in enumerate(prompt_list):
        print(f"\nDetecting: '{prompt}'")
        response_json = _call_sam3_roboflow_api(
            image_base64=image_base64,
            prompt=prompt,
            api_key=api_key,
            min_score=MIN_SCORE,
        )

        masks = _iter_masks_from_response(response_json, width, height)
        print(f"  masks: {len(masks)}")

        base_color = COLOR_PALETTE[prompt_idx % len(COLOR_PALETTE)]
        fill = (base_color[0], base_color[1], base_color[2], MASK_ALPHA)
        outline = (base_color[0], base_color[1], base_color[2], OUTLINE_ALPHA)

        for points in masks:
            overlay_draw.polygon(points, fill=fill, outline=outline)

            mask_img = Image.new("L", original.size, 0)
            mask_draw = ImageDraw.Draw(mask_img)
            mask_draw.polygon(points, fill=255, outline=255)

            bbox = mask_img.getbbox()
            if not bbox:
                continue

            crop = original.crop(bbox)
            mask_crop = mask_img.crop(bbox)
            crop.putalpha(mask_crop)

            label = _sanitize_label(prompt)
            crop_name = f"mask_{mask_index:03d}_{label}.png"
            crop.save(crops_dir / crop_name)
            mask_index += 1

    composite = Image.alpha_composite(original, overlay)
    overlay_path = output_dir / "overlay.png"
    composite.save(overlay_path)

    print(f"\nSaved overlay: {overlay_path}")
    print(f"Saved crops: {crops_dir}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
