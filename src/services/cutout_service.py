"""UI-agnostic cutout service for QuestCut-AI.

This module is the shared inference boundary for desktop, local web, and Docker
entrypoints. It intentionally avoids Qt widgets and file dialogs so callers can
use it from CLI/API contexts.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import BinaryIO, Iterable

from PIL import Image

from ..core.background_remover import BackgroundRemover
from ..core.portrait_mode import PortraitMode
from ..utils.constants import MODEL_CONFIG, MODEL_DISPLAY_ORDER


SUPPORTED_INPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
SUPPORTED_OUTPUT_FORMATS = {"png", "jpg", "jpeg", "webp"}


@dataclass(frozen=True)
class CutoutResult:
    """Result returned by the shared cutout service."""

    image: Image.Image
    mask: Image.Image
    model_key: str


class CutoutService:
    """Synchronous background-removal service shared across app surfaces."""

    def __init__(self):
        self._remover = BackgroundRemover()
        self._portrait = PortraitMode()
        self._lock = RLock()

    @staticmethod
    def available_models():
        """Return model metadata in display order."""
        return {
            key: MODEL_CONFIG[key]
            for key in MODEL_DISPLAY_ORDER
            if key in MODEL_CONFIG
        }

    @staticmethod
    def validate_model(model_key: str) -> str:
        """Validate and normalize a model key."""
        if model_key not in MODEL_CONFIG:
            raise ValueError(f"Unknown model: {model_key}")
        return model_key

    @staticmethod
    def validate_output_format(output_format: str) -> str:
        """Validate and normalize an output format."""
        fmt = (output_format or "png").lower().lstrip(".")
        if fmt not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}")
        return "jpg" if fmt == "jpeg" else fmt

    @staticmethod
    def load_image(source: str | Path | BinaryIO | Image.Image) -> Image.Image:
        """Load an input image from path, file-like object, or PIL image."""
        if isinstance(source, Image.Image):
            return source.copy()
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
                raise ValueError(f"Unsupported input image type: {path.suffix}")
            with Image.open(path) as image:
                return image.convert("RGBA")
        with Image.open(source) as image:
            return image.convert("RGBA")

    def remove_background(self, source: str | Path | BinaryIO | Image.Image, model_key: str = "birefnet") -> CutoutResult:
        """Remove background using the selected model and return RGBA image + mask."""
        model_key = self.validate_model(model_key)
        image = self.load_image(source)
        with self._lock:
            if model_key == "modnet":
                matte = self._portrait.process(image, async_mode=False)
                result = self._portrait.apply_matte(image, matte)
                return CutoutResult(image=result, mask=matte, model_key=model_key)
            if "rembg_model" not in MODEL_CONFIG[model_key]:
                raise ValueError(f"Model does not support background removal: {model_key}")
            result, mask = self._remover.remove_background_sync(image, model_name=model_key)
            return CutoutResult(image=result, mask=mask, model_key=model_key)

    def save_result(self, result: CutoutResult, output_path: str | Path, output_format: str | None = None, quality: int = 95) -> Path:
        """Save a cutout result to disk."""
        path = Path(output_path)
        fmt = self.validate_output_format(output_format or path.suffix or "png")
        path.parent.mkdir(parents=True, exist_ok=True)
        image = result.image
        if fmt in {"jpg", "webp"} and image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        save_format = "JPEG" if fmt == "jpg" else fmt.upper()
        save_kwargs = {"quality": int(quality)} if fmt in {"jpg", "webp"} else {"optimize": True}
        image.save(path, save_format, **save_kwargs)
        return path

    def process_file(self, input_path: str | Path, output_path: str | Path | None = None, model_key: str = "birefnet", output_format: str = "png") -> Path:
        """Process one file and write the result beside it or to output_path."""
        source = Path(input_path)
        fmt = self.validate_output_format(output_format)
        if output_path is None:
            output_path = source.with_name(f"{source.stem}_nobg.{fmt}")
        result = self.remove_background(source, model_key=model_key)
        return self.save_result(result, output_path, output_format=fmt)

    def process_files(self, input_paths: Iterable[str | Path], output_dir: str | Path, model_key: str = "birefnet", output_format: str = "png") -> list[Path]:
        """Process multiple files into output_dir."""
        out = Path(output_dir)
        fmt = self.validate_output_format(output_format)
        written = []
        for input_path in input_paths:
            source = Path(input_path)
            written.append(self.process_file(source, out / f"{source.stem}_nobg.{fmt}", model_key=model_key, output_format=fmt))
        return written


_service: CutoutService | None = None


def get_cutout_service() -> CutoutService:
    """Return the process-wide cutout service."""
    global _service
    if _service is None:
        _service = CutoutService()
    return _service
