# TRIBE v2 on Modal

GPU inference service for [facebookresearch/tribev2](https://github.com/facebookresearch/tribev2): upload a video, get a ZIP with `metadata.json` and `preds.npz` (compressed NumPy array `preds` of shape `(n_segments, n_vertices)`).

**Ortak kod:** HTTP API [`tribev2_modal/server.py`](tribev2_modal/server.py). [`app.py`](app.py) yalnızca Modal (GPU, volume, secret). **RunPod / RTX 6000** için aynı mantığı Docker ile çalıştır: [RUNPOD.md](RUNPOD.md) ve kökteki [Dockerfile](Dockerfile).

## Prerequisites

- Modal account and CLI: [modal.com](https://modal.com) — `pip install modal` then `modal setup`
- Hugging Face account with **gated** access to the LLaMA 3.2 model used by TRIBE (accept the license on the model page), then a **read** token

## 1. Create the Modal secret (Hugging Face token)

The app expects a secret named **`hf-secret`** (deployment plan). Replace `hf_...` with your token:

```bash
modal secret create hf-secret HUGGING_FACE_HUB_TOKEN=hf_xxxxxxxx
```

`HF_TOKEN` is also accepted by Hugging Face libraries if you prefer that key name.

If you already created a secret under another name (e.g. `tribev2-huggingface`), either rename it in the Modal dashboard or change `Secret.from_name(...)` in [app.py](app.py) to match.

### Optional: API key for your web app

Add keys to the **same** secret in the [Modal dashboard](https://modal.com/settings) (Secrets → `hf-secret`):

- `TRIBE_API_KEY` — if set, clients must send header `X-API-Key: <value>` on `POST /predict`.

## 2. Deploy

**Klasör:** `modal deploy` mutlaka `tribev2-modal` kökünden çalıştırılmalı (`tribev2_modal/` ve `app.py` aynı üst dizinde). Aksi halde imajda paket olmaz → **crash-loop / Containers: 0 live**.

```bash
cd tribev2-modal
modal deploy app.py
```

Modal prints a URL like `https://<workspace>--tribe-v2.modal.run`.

First request downloads weights to the `tribev2-cache` volume and can take a long time. If you hit **CUDA OOM**, edit [app.py](app.py) and set `gpu="A100-80GB"` (or another large-GPU string supported by your workspace).

### DataLoader / `closed file` hatası

Loglarda `ValueError: I/O operation on closed file` ve `DataLoader will create 20 worker` görürsen: varsayılan **20 worker** + geçici dosya çakışabiliyor. Kodda **`TRIBE_NUM_WORKERS=0`** (varsayılan) ve video **`/cache/input_uploads/`** altına yazılıyor. İstersen env ile `TRIBE_NUM_WORKERS=4` deneyebilirsin; önce 0 ile stabil çalışsın.

### Sunucuda otomatik kayıt (kayıp indirme olmasa bile)

Her başarılı tahminden sonra ZIP **sunucuda da** yazılır (varsayılan açık):

- Dizin: **`/cache/outputs/`** (Modal volume `tribev2-cache` ile kalıcı; `volume.commit` her çıktıda).
- Dosyalar: `*_videoadi_xxxxxxxx.zip` ve yanında aynı isimle **`*.job.json`** (job id + metadata özeti).
- HTTP yanıt başlıkları: **`X-Tribe-Job-Id`**, **`X-Tribe-Saved-Paths`** (sunucudaki `.zip` yolu/yolları).

Modal arayüzünde dosyaya **`serve > root` değil**, volume üzerinden bak: ilgili app / storage → **`tribev2-cache`** → mount **`/cache`** → **`outputs`**.

Kapatmak: function env **`TRIBE_SAVE_OUTPUTS=0`**. Ek dizin(ler): **`TRIBE_OUTPUT_DIRS=/cache/outputs,/cache/outputs2`** (virgülle).

## Terminalden ZIP indir (tek komut)

```bash
cd tribev2-modal
cp .env.example .env   # bir kez: içine TRIBE_API_URL=... yaz
./scripts/download_zip.sh /path/to/video.mp4
```

Çıktı varsayılan: `~/Desktop/tribe_predictions.zip`. İkinci argümanla dosya adı verilebilir.

## 3. Test

```bash
curl -sS -X POST "https://<workspace>--tribe-v2.modal.run/predict" \
  -H "X-API-Key: YOUR_KEY_IF_SET" \
  -F "file=@/path/to/video.mp4" \
  -o tribe_predictions.zip
unzip -l tribe_predictions.zip
```

Load predictions in Python:

```python
import json, zipfile, numpy as np
with zipfile.ZipFile("tribe_predictions.zip") as z:
    meta = json.loads(z.read("metadata.json"))
    with z.open("preds.npz") as f:
        data = np.load(f)
        preds = data["preds"]
print(meta, preds.shape)
```

### Health check

```bash
curl -sS "https://<workspace>--tribe-v2.modal.run/health"
```

## Web test arayüzü (hızlı deneme)

Statik sayfa; tarayıcıdan Modal API’ye bağlanır (CORS açık). **`index.html` dosyasına çift tıklayıp `file://` ile açma** — link çalışmaz / API engellenir. Mutlaka yerel sunucu kullan:

```bash
cd tribev2-modal/web
python3 serve.py
```

Varsayılan adres: **http://127.0.0.1:8765/** (tarayıcı çoğu zaman otomatik açılır). Port doluysa: `PORT=9000 python3 serve.py`

Alternatif: `python3 -m http.server 8765 --bind 127.0.0.1` sonra tarayıcıda aynı portu aç.

Modal kök URL’ini yapıştır (`https://<workspace>--tribe-v2.modal.run`), isteğe bağlı `X-API-Key`, video seç, **Çalıştır**.

### Vercel’de web arayüzü

1. [Vercel](https://vercel.com) → New Project → bu klasörü Git ile bağla (veya `web` klasörünü tek başına push et).
2. **Root Directory:** `web` (önemli: `api/config.js` ve `index.html` aynı kökte çalışsın).
3. **Environment Variables:** `TRIBE_API_URL` = `https://<workspace>--tribe-v2.modal.run` (sonunda `/` olmasın). Deploy sonrası sayfa açılınca bu adres otomatik dolar; istersen elle değiştirebilirsin.
4. Deploy. Açılan sitede video seç → **Çalıştır** → tarayıcı `tribe_<videoadı>_<tarih>.zip` dosyasını indirir (İndirilenler veya kaydet dediğin klasör).

Yerelde `python3 serve.py` ile `/api/config` olmadığı için URL’yi kendin yapıştırırsın; Vercel’de env ile gelir.

## Local smoke (no GPU required)

```bash
python scripts/smoke_local.py
```

## Web app contract (summary)

| Item | Value |
|------|--------|
| **Endpoint** | `POST /predict` |
| **Content-Type** | `multipart/form-data` |
| **Field name** | `file` (video file) |
| **Allowed extensions** | `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm` |
| **Response** | `application/zip` — `metadata.json` + `preds.npz` |
| **Auth** | Optional header `X-API-Key` if `TRIBE_API_KEY` is in the `hf-secret` Modal secret |
| **CORS** | Default `*`; set env `CORS_ORIGINS` on the function (comma-separated origins) for production browsers |
| **Upload limit** | Default 512 MB via `MAX_UPLOAD_MB` in [app.py](app.py) `env=`; change in code or override in Modal dashboard if your workspace supports it |
| **Timeout** | Function timeout 3600 s in [app.py](app.py); increase for very long videos |
| **Metadata** | `metadata.json` includes `tr_seconds` (fMRI TR) when available, shapes, dtypes |

For large files or long runs, consider async jobs and object storage later; synchronous `POST` is fine for shorter clips.

## License note

TRIBE v2 is [CC BY-NC 4.0](https://github.com/facebookresearch/tribev2/blob/main/LICENSE); check compliance for commercial use.
