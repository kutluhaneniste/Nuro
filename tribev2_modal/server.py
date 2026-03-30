"""FastAPI TRIBE v2 inference — Modal, Docker ve RunPod ile paylaşılır."""

import asyncio
import io
import json
import logging
import os
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

_model = None
_post_model_load_hook: Optional[Callable[[], None]] = None
_output_commit_hook: Optional[Callable[[], None]] = None


def set_post_model_load_hook(fn: Optional[Callable[[], None]]) -> None:
    """Modal volume.commit() gibi model yüklendikten sonra bir kez çalışacak callback (isteğe bağlı)."""
    global _post_model_load_hook
    _post_model_load_hook = fn


def set_output_commit_hook(fn: Optional[Callable[[], None]]) -> None:
    """Çıktı ZIP'i diske yazıldıktan sonra (Modal volume.commit vb.)."""
    global _output_commit_hook
    _output_commit_hook = fn


def _cache_root() -> str:
    return os.environ.get("TRIBE_CACHE_ROOT", "/cache")


def _dataloader_num_workers() -> int:
    """0 = ana süreçte yükle; çok worker + tempfile fork 'closed file' hatasına yol açabiliyor."""
    raw = os.environ.get("TRIBE_NUM_WORKERS", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _load_model():
    global _model
    if _model is not None:
        return _model
    root = _cache_root()
    hf_home = os.path.join(root, "hf")
    tribe_cache = os.path.join(root, "tribev2")
    os.makedirs(hf_home, exist_ok=True)
    os.makedirs(tribe_cache, exist_ok=True)
    os.environ.setdefault("HF_HOME", hf_home)
    os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(hf_home, "transformers"))
    os.environ.setdefault("TORCH_HOME", os.path.join(root, "torch"))

    from tribev2 import TribeModel

    nw = _dataloader_num_workers()
    logger.info("TRIBE loading with data.num_workers=%s", nw)
    _model = TribeModel.from_pretrained(
        "facebook/tribev2",
        cache_folder=tribe_cache,
        device="cuda",
        config_update={"data.num_workers": nw},
    )
    if _post_model_load_hook is not None:
        try:
            _post_model_load_hook()
        except Exception as e:
            logger.warning("post_model_load_hook failed: %s", e)
    return _model


def _optional_api_key() -> Optional[str]:
    return os.environ.get("TRIBE_API_KEY") or os.environ.get("API_KEY")


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    out = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return (out[:80] or "video").strip("_") or "video"


def _save_zip_to_disk(
    zip_bytes: bytes,
    meta: dict,
    original_filename: str,
    job_id: str,
) -> List[str]:
    """ZIP + küçük meta JSON'u bir veya daha fazla dizine yazar. Dönen: yazılan dosya yolları."""
    flag = os.environ.get("TRIBE_SAVE_OUTPUTS", "1").strip().lower()
    if flag in ("0", "false", "no"):
        return []

    extra = os.environ.get("TRIBE_OUTPUT_DIRS", "").strip()
    if extra:
        dirs = [d.strip() for d in extra.split(",") if d.strip()]
    else:
        dirs = [os.path.join(_cache_root(), "outputs")]

    stem = _safe_stem(original_filename)
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    base = f"{ts}_{stem}_{job_id[:8]}"
    zip_name = base + ".zip"
    side_name = base + ".job.json"

    saved: List[str] = []
    sidecar = {
        "job_id": job_id,
        "created_utc": ts,
        "original_filename": original_filename,
        "metadata": meta,
        "zip_filename": zip_name,
    }

    for d in dirs:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            zp = os.path.join(d, zip_name)
            jp = os.path.join(d, side_name)
            with open(zp, "wb") as f:
                f.write(zip_bytes)
            with open(jp, "w", encoding="utf-8") as f:
                json.dump(sidecar, f, indent=2)
            saved.append(zp)
            saved.append(jp)
            logger.info("Saved output: %s", zp)
        except OSError as e:
            logger.error("Failed to save output under %s: %s", d, e)

    if saved and _output_commit_hook is not None:
        try:
            _output_commit_hook()
        except Exception as e:
            logger.warning("output_commit_hook failed: %s", e)

    return saved


def _check_api_key(x_api_key: Optional[str], http_exc_cls: Any) -> None:
    expected = _optional_api_key()
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise http_exc_cls(status_code=401, detail="Invalid or missing X-API-Key")


def _run_predict(video_bytes: bytes, suffix: str) -> Tuple[dict, bytes]:
    import numpy as np

    model = _load_model()
    suf = suffix if suffix.startswith(".") else f".{suffix}"
    uploads = os.path.join(_cache_root(), "input_uploads")
    os.makedirs(uploads, exist_ok=True)
    tmp_path = os.path.join(uploads, f"{uuid.uuid4().hex}{suf}")
    try:
        with open(tmp_path, "wb") as f:
            f.write(video_bytes)
        df = model.get_events_dataframe(video_path=tmp_path)
        preds, segments = model.predict(events=df, verbose=False)
        tr = getattr(getattr(model, "data", None), "TR", None)
        meta = {
            "preds_shape": list(preds.shape),
            "preds_dtype": str(preds.dtype),
            "n_segments": int(preds.shape[0]),
            "n_vertices": int(preds.shape[1]) if preds.ndim == 2 else None,
            "n_segment_objects": len(segments),
            "tr_seconds": float(tr) if tr is not None else None,
        }
        bio = io.BytesIO()
        np.savez_compressed(bio, preds=preds)
        return meta, bio.getvalue()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import Response
    from starlette.requests import Request

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_model)
        yield

    web = FastAPI(title="TRIBE v2 API", lifespan=lifespan)

    from fastapi.middleware.cors import CORSMiddleware

    _cors = os.environ.get("CORS_ORIGINS", "*").strip()
    _origins = (
        [o.strip() for o in _cors.split(",") if o.strip()]
        if _cors != "*"
        else ["*"]
    )
    web.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Disposition",
            "X-Tribe-Job-Id",
            "X-Tribe-Saved-Paths",
        ],
    )

    @web.get("/health")
    async def health():
        return {"status": "ok", "model_loaded": _model is not None}

    @web.post("/predict")
    async def predict(request: Request):
        x_api_key = request.headers.get("X-API-Key")
        _check_api_key(x_api_key, HTTPException)
        form = await request.form()
        file = form.get("file")
        if file is None:
            raise HTTPException(status_code=400, detail='Missing form field "file"')
        filename = getattr(file, "filename", None) or ""
        if not filename:
            raise HTTPException(status_code=400, detail="Missing filename")
        suffix = Path(filename).suffix.lower() or ".mp4"
        allowed = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
        if suffix not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported extension {suffix}; allowed: {sorted(allowed)}",
            )
        raw = await file.read()
        max_bytes = int(os.environ.get("MAX_UPLOAD_MB", "512")) * 1024 * 1024
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {max_bytes // (1024 * 1024)} MB)",
            )
        loop = asyncio.get_event_loop()
        try:
            meta, npz_bytes = await loop.run_in_executor(
                None, lambda: _run_predict(raw, suffix)
            )
        except Exception as e:
            logger.exception("predict failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

        meta["original_filename"] = filename
        job_id = str(uuid.uuid4())
        meta["job_id"] = job_id

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps(meta, indent=2))
            zf.writestr("preds.npz", npz_bytes)
        body = zip_buf.getvalue()

        saved_paths = _save_zip_to_disk(body, meta, filename, job_id)
        resp_headers = {
            "Content-Disposition": 'attachment; filename="tribe_predictions.zip"',
            "X-Tribe-Job-Id": job_id,
        }
        if saved_paths:
            # ZIP yolları (job.json hariç tekrar etmeyelim — sadece .zip)
            zips_only = [p for p in saved_paths if p.endswith(".zip")]
            resp_headers["X-Tribe-Saved-Paths"] = "|".join(zips_only)

        return Response(
            content=body,
            media_type="application/zip",
            headers=resp_headers,
        )

    return web


# Uvicorn (Docker / RunPod): uvicorn tribev2_modal.server:create_app --factory --host 0.0.0.0 --port 8000
