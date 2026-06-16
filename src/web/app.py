"""FastAPI app for local browser and Docker deployments.

The web layer stays thin: validation, upload limits, and HTTP responses live here;
model loading and background removal stay in src.services.cutout_service.
"""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError

from src.services.cutout_service import (
    SUPPORTED_INPUT_SUFFIXES,
    CutoutService,
    get_cutout_service,
)
from src.utils.constants import APP_NAME, APP_VERSION

DEFAULT_MAX_UPLOAD_MB = 25
INDEX_HTML = Path(__file__).with_name("static") / "index.html"
MIME_BY_FORMAT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
router = APIRouter()


def _max_upload_bytes() -> int:
    raw = os.environ.get("QUESTCUT_MAX_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB))
    try:
        mb = max(1, int(raw))
    except ValueError:
        mb = DEFAULT_MAX_UPLOAD_MB
    return mb * 1024 * 1024


def _service() -> CutoutService:
    return get_cutout_service()


def _normalize_filename(name: str | None) -> str:
    stem = Path(name or "image").stem or "image"
    safe = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) else "_"
        for ch in stem
    ).strip("_")
    return safe or "image"


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def _model_payload(service: CutoutService) -> dict:
    return {
        "models": [
            {
                "key": key,
                "name": cfg.get("name", key),
                "display_name": cfg.get("display_name", cfg.get("name", key)),
                "description": cfg.get("description", ""),
                "size": cfg.get("size", ""),
                "category": cfg.get("category", ""),
            }
            for key, cfg in service.available_models().items()
        ]
    }


async def _read_upload(file: UploadFile) -> bytes:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in SUPPORTED_INPUT_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {suffix}")

    max_upload = _max_upload_bytes()
    data = await file.read(max_upload + 1)
    if len(data) > max_upload:
        raise HTTPException(status_code=413, detail=f"Upload is larger than {max_upload // (1024 * 1024)}MB")
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    return data


def _flatten_for_opaque_format(image: Image.Image, fmt: str) -> Image.Image:
    if fmt not in {"jpg", "jpeg"} or image.mode != "RGBA":
        return image
    background = Image.new("RGB", image.size, (255, 255, 255))
    background.paste(image, mask=image.split()[3])
    return background


def _stream_image(image: Image.Image, fmt: str, filename: str) -> StreamingResponse:
    out = BytesIO()
    save_image = _flatten_for_opaque_format(image, fmt)
    save_image.save(out, "JPEG" if fmt in {"jpg", "jpeg"} else fmt.upper())
    out.seek(0)
    return StreamingResponse(
        out,
        media_type=MIME_BY_FORMAT[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@router.get("/api/models")
def models(service: CutoutService = Depends(_service)):
    return _model_payload(service)


@router.post("/api/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    model_key: str = Form("birefnet"),
    output_format: str = Form("png"),
    service: CutoutService = Depends(_service),
):
    data = await _read_upload(file)
    try:
        fmt = service.validate_output_format(output_format)
        service.validate_model(model_key)
        with Image.open(BytesIO(data)) as probe:
            image = probe.convert("RGBA")
        result = await run_in_threadpool(service.remove_background, image, model_key=model_key)
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    output_name = f"{_normalize_filename(file.filename)}_nobg.{fmt}"
    return _stream_image(result.image, fmt, output_name)


@router.get("/", response_class=HTMLResponse)
def index():
    return _index_html()


def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME, version=APP_VERSION)
    app.include_router(router)
    return app


app = create_app()
