# Nuro — Neural Attention Analytics

> What is happening inside the viewer's brain while they watch?

Nuro is a neural attention analytics platform that reveals how content *feels* to viewers — second by second — using brain encoding AI.

Content creators and ad agencies measure performance with behavioral proxies: watch time, CTR, scroll depth. These answer *how much*, never *how*. Nuro answers the real question: **what is the viewer's brain doing at each moment?**

**[Live demo →](https://tribev2-modal.vercel.app)**

---

## How It Works

```
YouTube URL
    ↓
GPU Server (Modal / A100)
    → Download video via yt-dlp
    → Extract audio, video frames, transcript
    → TRIBE v2 brain encoding inference
    → Output: (n_seconds × 20,484) cortical activation matrix
    → Compute 4 metrics, normalize 0–100
    ↓
Claude Opus API
    → Identify peak engagement windows, drops, spikes
    → Generate actionable insight cards per moment
    ↓
Next.js Dashboard (Vercel)
    → Interactive second-by-second chart
    → Metric lines with hover tooltips
    → Insight cards with timestamps + recommendations
```

---

## The Brain Encoding Model — TRIBE v2

**Source:** Meta FAIR (Fundamental AI Research)
**Paper:** *"A foundation model of vision, audition, and language for in-silico neuroscience"* — ICLR 2026
**Weights:** `facebook/tribev2` on HuggingFace

TRIBE v2 is a trimodal foundation model trained on 1,000+ hours of fMRI recordings from 720 subjects. It predicts high-resolution brain responses to any audio-visual stimulus — without requiring actual brain scans.

| Input | Encoder | Brain Region |
|-------|---------|-------------|
| Video frames | V-JEPA2 | Visual cortex (V1–V4, LO) |
| Audio | Wav2Vec-BERT | Auditory cortex |
| Transcript | Llama 3.2 | Language network (Broca, STG) |

Output: `(n_seconds × 20,484)` — predicted fMRI activation for every cortical vertex, every second. Every number corresponds to a real brain region with known function. This is not a proxy metric — it is a simulation of neural activity validated against decades of empirical neuroscience.

---

## 4 Metrics

```python
attention  = preds[:, 0:500].mean(axis=1)     # Visual cortex (V1–V4)
emotional  = preds[:, 1500:2000].mean(axis=1) # Default Mode Network
cognitive  = preds[:, 1000:1500].mean(axis=1) # Language network (Broca)
memory     = preds[:, 2000:2200].mean(axis=1) # Parahippocampal gyrus

# Normalize to 0-100
normalized = (x - x.min()) / (x.max() - x.min()) * 100
```

| Metric | Brain Region | High = |
|--------|-------------|--------|
| **Attention** | Visual cortex (V1-V4) | Eyes locked, full visual engagement |
| **Emotional** | Default Mode Network | "This means something to me" |
| **Cognitive Load** | Language network (Broca) | Complex message being processed |
| **Memorability** | Parahippocampal gyrus | This moment will be remembered |

---

## Architecture

```
Next.js (Vercel)
    -> /api/analyze (Next.js API route)
    -> Modal GPU endpoint (FastAPI + TRIBE v2)
    -> Claude Opus API (insight generation)
    -> Combined JSON response to frontend
```

- **GPU:** A100 40/80GB on Modal (auto-scaling) or RunPod
- **Inference time:** ~5-10 min per 10-minute video
- **Cost per analysis:** ~$0.50-1.00 GPU + ~$0.05-0.10 Claude API -> ~98% gross margin at $75/analysis

---

## Competitive Landscape

| | Nuro | Neurons AI | Tobii | Focus Group |
|--|------|-----------|-------|-------------|
| Method | Brain encoding AI | Eye-tracking + EEG | Eye-tracking | Survey |
| Input | Any video URL | Static images | Video/screen | Physical session |
| Speed | Minutes | Minutes | Minutes | Weeks |
| Cost | ~$75 | ~$500+ | Hardware required | $5,000-50,000 |

---

## Deployment

This repo contains the GPU inference backend deployed on [Modal](https://modal.com).

**Requirements:** Modal account, Hugging Face token with access to `facebook/tribev2`

```bash
# Set up Modal secret (HuggingFace token)
modal secret create hf-secret HUGGING_FACE_HUB_TOKEN=hf_your_token

# Deploy
cd tribev2-modal
modal deploy app.py
```

For RunPod deployment, see [RUNPOD.md](RUNPOD.md).

**Test the endpoint:**
```bash
curl -X POST "https://your-workspace--tribe-v2.modal.run/predict" \
  -F "file=@/path/to/video.mp4" \
  -o predictions.zip
```

---

## Tech Stack

`Python` `FastAPI` `PyTorch` `Modal` `Next.js` `TypeScript` `Tailwind CSS` `Claude Opus API` `yt-dlp`

---

*Built by [Kutluhan Eniste](https://www.linkedin.com/in/kutluhan-eniste) - Istanbul, Turkey*
*TRIBE v2 is CC-BY-NC-4.0 (Meta FAIR)*
