from pathlib import Path
from typing import Annotated
import traceback

from PIL import Image, ImageOps
from pydantic import Field
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("image-inverter")


def resolve_safe_path(workspace_dir: str, image_relative_path: str) -> tuple[Path, Path]:
    """
    Resolve and validate image path.

    Returns:
        workspace_path, input_image_path
    """
    workspace_path = Path(workspace_dir).expanduser().resolve()

    if not workspace_path.exists():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    if not workspace_path.is_dir():
        raise ValueError(f"Workspace path is not a directory: {workspace_path}")

    relative_path = Path(image_relative_path)

    if relative_path.is_absolute():
        raise ValueError("image_relative_path must be a relative path, not an absolute path")

    input_image_path = (workspace_path / relative_path).resolve()

    try:
        input_image_path.relative_to(workspace_path)
    except ValueError:
        raise ValueError("image_relative_path escapes the workspace directory")

    if not input_image_path.exists():
        raise ValueError(f"Image file does not exist: {image_relative_path}")

    if not input_image_path.is_file():
        raise ValueError(f"Input path is not a file: {image_relative_path}")

    return workspace_path, input_image_path


def make_output_path(input_image_path: Path) -> Path:
    """
    Generate output path in the same directory as the input image.
    Avoid overwriting existing files.
    """
    suffix = input_image_path.suffix or ".png"
    base_output_path = input_image_path.with_name(
        f"{input_image_path.stem}_inverted{suffix}"
    )

    if not base_output_path.exists():
        return base_output_path

    for i in range(1, 1000):
        candidate = input_image_path.with_name(
            f"{input_image_path.stem}_inverted_{i}{suffix}"
        )
        if not candidate.exists():
            return candidate

    raise ValueError("Could not generate a unique output filename")


def invert_image(input_image_path: Path, output_image_path: Path) -> None:
    """
    Invert image colors and save to output path.
    Preserves alpha channel if present.
    """
    with Image.open(input_image_path) as image:
        image_format = image.format

        if image.mode in ("RGBA", "LA") or "A" in image.getbands():
            rgba = image.convert("RGBA")
            r, g, b, a = rgba.split()

            rgb = Image.merge("RGB", (r, g, b))
            inverted_rgb = ImageOps.invert(rgb)

            r2, g2, b2 = inverted_rgb.split()
            output_image = Image.merge("RGBA", (r2, g2, b2, a))
        else:
            rgb = image.convert("RGB")
            output_image = ImageOps.invert(rgb)

        # JPEG does not support alpha channel
        if output_image_path.suffix.lower() in [".jpg", ".jpeg"]:
            output_image = output_image.convert("RGB")

        output_image.save(output_image_path, format=image_format)


@mcp.tool()
async def invert_image_colors(
    workspace_dir: Annotated[
        str,
        Field(
            description=(
                "Absolute workspace directory path. "
                "Windows example: D:/mcp_workspace. "
                "Linux/macOS example: /home/user/mcp_workspace. "
                )
            )
    ],
    image_relative_path: Annotated[
        str,
        Field(description="Image file path relative to workspace_dir, such as images/demo.png")
    ],
) -> dict:
    """
    Read an image under the workspace directory, invert its colors,
    and save the result image in the same directory.
    """
    try:
        workspace_path, input_image_path = resolve_safe_path(
            workspace_dir,
            image_relative_path
        )

        output_image_path = make_output_path(input_image_path)

        invert_image(input_image_path, output_image_path)

        output_relative_path = output_image_path.relative_to(workspace_path).as_posix()

        return {
            "result": "success",
            "image_relative_path": output_relative_path
        }

    except Exception as e:
        return {
            "result": "error",
            "error": str(e)
        }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()