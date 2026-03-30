# RunPod (RTX 6000 Pro vb.) — TRIBE API

Uygulama: **`tribev2_modal/server.py`** — `GET /health`, `POST /predict` (multipart `file`).

---

## SSH ile bağlan (önerilen)

RunPod pod sayfasında **Connect** → **SSH** komutunu kopyala (ör. `ssh root@xxx -p 12345`). İlk bağlantıda anahtar eklemen istenebilir; RunPod dokümantasyonuna göre **public key** ekle.

### 1) Kendi Mac’inden projeyi pod’a at

Yerel terminalde (`tribev2-modal` masaüstünde varsayalım):

```bash
# RunPod'un verdiği host ve port ile (örnek)
scp -P 12345 -r ~/Desktop/tribev2-modal root@IP_ADRESI:/workspace/
```

`IP_ADRESI`, `12345` ve kullanıcı (`root` / `ubuntu`) pod ekranındaki değerlerle değişir.

Alternatif: **`rsync`** (tekrar gönderimde hızlı):

```bash
rsync -avz -e "ssh -p 12345" ~/Desktop/tribev2-modal/ root@IP_ADRESI:/workspace/tribev2-modal/
```

### 2) SSH ile pod’a gir

```bash
ssh -p 12345 root@IP_ADRESI
```

### 3) Pod içinde — token ve Docker

```bash
cd /workspace/tribev2-modal
export HUGGING_FACE_HUB_TOKEN="hf_XXXXXXXXX"

mkdir -p /workspace/cache
docker build -t tribe-v2-api .

docker run -d --name tribe-v2 --gpus all \
  -p 8000:8000 \
  -e HUGGING_FACE_HUB_TOKEN \
  -e TRIBE_NUM_WORKERS=0 \
  -v /workspace/cache:/workspace/cache \
  tribe-v2-api
```

RunPod arayüzünde **TCP port 8000**’i dışarı aç (HTTP proxy / public URL).

### 4) Test

Pod **içinde**:

```bash
curl -sS http://127.0.0.1:8000/health
```

Kendi Mac’inden (RunPod’un verdiği **public URL** ile):

```bash
curl -sS https://SENIN_RUNPOD_PUBLIC_URL/health
```

### 5) Durdur

```bash
docker stop tribe-v2 && docker rm tribe-v2
```

---

## Web terminal (SSH istemezsen)

RunPod’un tarayıcı terminalinde aynı komutları çalıştırabilirsin; dosyayı önce **RunPod file upload** veya `scp` ile `/workspace`’a koyman gerekir.

---

## Ortam değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `HUGGING_FACE_HUB_TOKEN` veya `HF_TOKEN` | Zorunlu (gated LLaMA) |
| `TRIBE_API_KEY` | İsteğe bağlı; istemci `X-API-Key` gönderir |
| `TRIBE_NUM_WORKERS` | Varsayılan `0` (Dockerfile / öneri) |
| `TRIBE_CACHE_ROOT` | Varsayılan `/workspace/cache` |

---

## Sorun giderme

- **Docker yok:** GPU template’de Docker’lı imaj seç veya `pytorch` + manuel `pip install` (uzun).
- **Build hata:** `Dockerfile` içindeki `FROM pytorch/...` satırını pod’un CUDA sürümüne uygun imajla değiştir.
- **Port:** Dışarıdan erişim için RunPod **port 8000** yönlendirmesini aç.

---

## Modal ile fark

| | Modal | RunPod + Docker |
|--|--------|-----------------|
| Önbellek | Modal Volume | `/workspace/cache` volume |
| Secret | `hf-secret` | `export` veya RunPod env |
| Kod | `modal deploy app.py` | `docker build` + `docker run` |
