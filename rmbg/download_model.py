"""
下载 BRIA RMBG-2.0 模型到本地。

只下载本地 transformers 推理需要的文件：
- config.json
- preprocessor_config.json
- BiRefNet_config.py
- birefnet.py
- model.safetensors

不会下载：
- onnx/
- pytorch_model.bin
- README.md
- 示例图片

使用方式：
1. 将 HF_TOKEN 替换为你自己的 HuggingFace Read token。
2. 确认你已经在 HuggingFace 申请并获准访问 briaai/RMBG-2.0。
3. 运行：python download_rmbg2_model.py
"""

from pathlib import Path

from huggingface_hub import snapshot_download


# ===================== 硬编码配置 =====================
 # TODO: 替换为你的 HuggingFace token

MODEL_REPO_ID = "briaai/RMBG-2.0"
LOCAL_MODEL_DIR = "rmbg/models/RMBG-2.0"

# 只下载 transformers 本地推理需要的文件
ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "BiRefNet_config.py",
    "birefnet.py",
    "model.safetensors",
]
# ======================================================


def main() -> None:
    local_dir = Path(LOCAL_MODEL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"开始下载模型: {MODEL_REPO_ID}")
    print(f"保存目录: {local_dir.resolve()}")
    print("下载文件白名单:")
    for pattern in ALLOW_PATTERNS:
        print(f"  - {pattern}")

    snapshot_download(
        repo_id=MODEL_REPO_ID,
        token=HF_TOKEN,
        local_dir=str(local_dir),
        allow_patterns=ALLOW_PATTERNS,
    )

    print("\n模型下载完成。")
    print(f"本地模型目录: {local_dir.resolve()}")


if __name__ == "__main__":
    main()