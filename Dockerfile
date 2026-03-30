# TRIBE v2 API — RunPod, local GPU, veya herhangi bir NVIDIA Docker host
# Build: docker build -t tribe-v2-api .
# Run:  docker run --gpus all -p 8000:8000 -e HUGGING_FACE_HUB_TOKEN=hf_xxx -v tribe-cache:/workspace/cache tribe-v2-api

FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 git ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY tribev2_modal /app/tribev2_modal

# Base image already has torch; tribev2 pins compatible stack
RUN pip install --no-cache-dir fastapi python-multipart "uvicorn[standard]" \
    && pip install --no-cache-dir "git+https://github.com/facebookresearch/tribev2.git" \
    && python -m spacy download en_core_web_sm

ENV PYTHONUNBUFFERED=1
ENV TRIBE_CACHE_ROOT=/workspace/cache
ENV TRIBE_NUM_WORKERS=0

EXPOSE 8000

CMD ["uvicorn", "tribev2_modal.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
