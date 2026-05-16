"""Replace draw.io placeholders with RMBG outputs.

Outputs:
- final.drawio
"""

from __future__ import annotations

import base64
import json
import xml.etree.ElementTree as ET
from pathlib import Path


# ---- Hardcoded configuration ----
ICON_INFOS_JSON = (
    "step3/icon_rmbg_outputs/Validation_Framework_Medical_Vision_202605151644/icon_infos.json"
)
TEMPLATE_DRAWIO = "step4/template/Validation_Framework_Medical_Vision_202605151644/template.drawio"
OUTPUT_DRAWIO = "step5/final/Validation_Framework_Medical_Vision_202605151644/final.drawio"


def _load_icon_infos(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    raise ValueError("icon_infos.json must be a list")


def _image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _find_cell_by_id(root: ET.Element, cell_id: str) -> ET.Element | None:
    return root.find(f".//mxCell[@id='{cell_id}']")


def run() -> None:
    icon_infos_path = Path(ICON_INFOS_JSON)
    template_drawio_path = Path(TEMPLATE_DRAWIO)
    output_drawio_path = Path(OUTPUT_DRAWIO)
    output_drawio_path.parent.mkdir(parents=True, exist_ok=True)

    if not icon_infos_path.is_file():
        raise FileNotFoundError(f"icon_infos.json not found: {icon_infos_path}")
    if not template_drawio_path.is_file():
        raise FileNotFoundError(f"template.drawio not found: {template_drawio_path}")

    icon_infos = _load_icon_infos(icon_infos_path)

    tree = ET.parse(str(template_drawio_path))
    root = tree.getroot()

    for info in icon_infos:
        label_clean = str(info.get("label_clean", "")).strip()
        if not label_clean:
            print("Skip icon with empty label_clean")
            continue

        nobg_path = Path(str(info.get("nobg_path", "")))
        if not nobg_path.is_file():
            print(f"Missing nobg icon: {nobg_path}")
            continue

        cell = _find_cell_by_id(root, label_clean)
        if cell is None:
            print(f"Placeholder not found in drawio: {label_clean}")
            continue

        x1 = str(info.get("x1", 0))
        y1 = str(info.get("y1", 0))
        width = str(info.get("width", 0))
        height = str(info.get("height", 0))

        image_b64 = _image_to_base64(nobg_path)
        style = (
            "shape=image;"
            "html=1;"
            "imageAspect=0;"
            "aspect=fixed;"
            f"image=data:image/png%3Bbase64,{image_b64};"
        )

        cell.set("style", style)
        cell.set("value", "")
        cell.set("vertex", "1")

        geometry = cell.find("mxGeometry")
        if geometry is None:
            geometry = ET.SubElement(cell, "mxGeometry")
            geometry.set("as", "geometry")

        geometry.set("x", x1)
        geometry.set("y", y1)
        geometry.set("width", width)
        geometry.set("height", height)

        print(f"Replaced: {label_clean}")

    tree.write(str(output_drawio_path), encoding="utf-8", xml_declaration=True)
    print(f"Saved: {output_drawio_path}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
