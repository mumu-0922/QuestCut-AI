"""FastAPI app for local browser and Docker deployments.

The web layer stays thin: validation, upload limits, and HTTP responses live here;
model loading and background removal stay in src.services.cutout_service.
"""
from __future__ import annotations

import os
import zipfile
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


def _encode_image(image: Image.Image, fmt: str) -> bytes:
    out = BytesIO()
    save_image = _flatten_for_opaque_format(image, fmt)
    save_image.save(out, "JPEG" if fmt in {"jpg", "jpeg"} else fmt.upper())
    return out.getvalue()


def _process_upload_data(
    filename: str | None,
    data: bytes,
    model_key: str,
    output_format: str,
    service: CutoutService,
) -> tuple[str, bytes, str]:
    fmt = service.validate_output_format(output_format)
    service.validate_model(model_key)
    with Image.open(BytesIO(data)) as probe:
        image = probe.convert("RGBA")
    result = service.remove_background(image, model_key=model_key)
    output_name = f"{_normalize_filename(filename)}_nobg.{fmt}"
    return output_name, _encode_image(result.image, fmt), MIME_BY_FORMAT[fmt]


def _stream_bytes(content: bytes, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _unique_zip_name(used: set[str], filename: str) -> str:
    path = Path(filename)
    candidate = filename
    index = 1
    while candidate in used:
        candidate = f"{path.stem}_{index}{path.suffix}"
        index += 1
    used.add(candidate)
    return candidate


def _error_detail(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    return str(exc) or type(exc).__name__


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
        output_name, content, media_type = await run_in_threadpool(
            _process_upload_data,
            file.filename,
            data,
            model_key,
            output_format,
            service,
        )
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    return _stream_bytes(content, media_type, output_name)


@router.post("/api/remove-background-batch")
async def remove_background_batch(
    files: list[UploadFile] = File(...),
    model_key: str = Form("birefnet"),
    output_format: str = Form("png"),
    service: CutoutService = Depends(_service),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    used_names: set[str] = set()
    errors: list[str] = []
    written = 0
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            try:
                data = await _read_upload(file)
                output_name, content, _ = await run_in_threadpool(
                    _process_upload_data,
                    file.filename,
                    data,
                    model_key,
                    output_format,
                    service,
                )
                zf.writestr(_unique_zip_name(used_names, output_name), content)
                written += 1
            except Exception as exc:  # Keep batch jobs useful when one file fails.
                errors.append(f"{file.filename or 'image'}: {_error_detail(exc)}")
        if errors:
            zf.writestr("errors.txt", "\n".join(errors))

    if written == 0:
        raise HTTPException(status_code=400, detail="All files failed: " + "; ".join(errors))

    zip_buffer.seek(0)
    return _stream_bytes(zip_buffer.getvalue(), "application/zip", "QuestCut-AI-batch.zip")


@router.get("/", response_class=HTMLResponse)
def index():
    return _index_html()


def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME, version=APP_VERSION)
    app.include_router(router)
    return app


app = create_app()
