"""Modal deploy: GPU + volume + secrets; asıl API kodu tribev2_modal.server içinde."""

# modal deploy bu dosyanın olduğu klasörden çalıştırılmalı (tribev2_modal/ yanında olmalı).

import modal

from tribev2_modal.server import (
    create_app,
    set_output_commit_hook,
    set_post_model_load_hook,
)

APP_NAME = "tribe-v2-inference"
CACHE_MOUNT = "/cache"

cache_vol = modal.Volume.from_name("tribev2-cache", create_if_missing=True)

tribe_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "ffmpeg",
        "libsndfile1",
        "git",
        "curl",
        "ca-certificates",
        "build-essential",
    )
    .pip_install(
        "torch==2.6.0",
        "torchvision==0.21.0",
        extra_index_url="https://download.pytorch.org/whl/cu124",
    )
    .pip_install("fastapi", "python-multipart", "uvicorn[standard]")
    .run_commands(
        "pip install 'git+https://github.com/facebookresearch/tribev2.git'",
    )
    .run_commands(
        "python -m spacy download en_core_web_sm",
    )
    # Yoksa konteyner tribev2_modal bulamaz → crash-loop (ModuleNotFoundError).
    .add_local_python_source("tribev2_modal", copy=True)
)

app = modal.App(APP_NAME)


@app.function(
    image=tribe_image,
    gpu="A100",
    volumes={CACHE_MOUNT: cache_vol},
    secrets=[modal.Secret.from_name("hf-secret")],
    timeout=60 * 60,
    scaledown_window=60 * 10,
    env={
        "MAX_UPLOAD_MB": "512",
        "TRIBE_CACHE_ROOT": CACHE_MOUNT,
        "TRIBE_NUM_WORKERS": "0",
    },
)
@modal.asgi_app(label="tribe-v2")
def serve():
    def vol_commit():
        try:
            cache_vol.commit()
        except Exception:
            pass

    set_post_model_load_hook(vol_commit)
    set_output_commit_hook(vol_commit)
    return create_app()
