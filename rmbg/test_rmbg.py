from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


# =========================
# 硬编码路径
# =========================
MODEL_DIR = "rmbg/models/RMBG-2.0"

INPUT_IMAGE_PATH = "rmbg/sample_images/Snipaste_2026-05-15_17-36-13.jpg"
OUTPUT_IMAGE_PATH = f"rmbg/rmbg_outputs/{Path(INPUT_IMAGE_PATH).stem}_nobg.png"


def remove_background(
    input_image_path: str,
    output_image_path: str,
    model_dir: str,
) -> None:
    model_dir = Path(model_dir)
    input_image_path = Path(input_image_path)
    output_image_path = Path(output_image_path)

    if not model_dir.exists():
        raise FileNotFoundError(f"本地模型目录不存在: {model_dir}")

    if not input_image_path.exists():
        raise FileNotFoundError(f"输入图像不存在: {input_image_path}")

    output_image_path.parent.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # device = "cpu"
    print(f"使用设备: {device}")
    print(f"加载本地模型: {model_dir}")

    model = AutoModelForImageSegmentation.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
    ).eval().to(device)

    image_size = (1024, 1024)

    transform_image = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225],
        ),
    ])

    image = Image.open(input_image_path).convert("RGB")
    input_tensor = transform_image(image).unsqueeze(0).to(device)

    with torch.no_grad():
        pred = model(input_tensor)[-1].sigmoid().cpu()

    mask = pred[0].squeeze()
    mask_pil = transforms.ToPILImage()(mask)
    mask_pil = mask_pil.resize(image.size)

    output = image.copy()
    output.putalpha(mask_pil)
    output.save(output_image_path)

    print(f"去背景结果已保存: {output_image_path}")


if __name__ == "__main__":
    remove_background(
        input_image_path=INPUT_IMAGE_PATH,
        output_image_path=OUTPUT_IMAGE_PATH,
        model_dir=MODEL_DIR,
    )