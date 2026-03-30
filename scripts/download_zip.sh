#!/usr/bin/env bash
# Terminalden video gönder, ZIP'i indir. Uzun işler için max bekleme 2 saat.
# Kullanım:
#   export TRIBE_API_URL="https://xxx--tribe-v2.modal.run"
#   ./scripts/download_zip.sh /path/to/video.mp4
# veya: cp .env.example .env  → TRIBE_API_URL doldur → aynı komut
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$ROOT/.env"
  set +a
fi

API="${TRIBE_API_URL:-}"
KEY="${TRIBE_API_KEY:-}"
VIDEO="${1:-}"
OUT="${2:-$HOME/Desktop/tribe_predictions.zip}"

if [[ -z "$API" ]]; then
  echo "TRIBE_API_URL yok."
  echo "  export TRIBE_API_URL='https://...--tribe-v2.modal.run'"
  echo "veya:  cp $ROOT/.env.example $ROOT/.env  ve düzenle"
  exit 1
fi
API="${API%/}"

if [[ -z "$VIDEO" ]] || [[ ! -f "$VIDEO" ]]; then
  echo "Kullanım: $0 /path/to/video.mp4 [çıktı.zip]"
  echo "Örnek:    $0 ~/Movies/kisa.mp4"
  exit 1
fi

echo "→ ${API}/predict"
echo "→ Video: $VIDEO"
echo "→ Çıktı: $OUT"
echo ""

EXTRA=()
if [[ -n "${KEY}" ]]; then
  EXTRA+=(-H "X-API-Key: ${KEY}")
fi

HDRF=$(mktemp)
HTTP_CODE=$(curl -sS --max-time 7200 --connect-timeout 120 \
  -o "$OUT" -w "%{http_code}" \
  -D "$HDRF" \
  -X POST "${API}/predict" \
  "${EXTRA[@]}" \
  -F "file=@${VIDEO}")

echo ""
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Hata: HTTP $HTTP_CODE"
  echo "Yanıt (dosya veya JSON olabilir):"
  head -c 4000 "$OUT" 2>/dev/null || true
  echo ""
  rm -f "$HDRF"
  exit 1
fi

echo "Tamam: $OUT"
echo "Sunucu (Modal volume /cache/outputs):"
grep -iE '^(X-Tribe-Job-Id|X-Tribe-Saved-Paths):' "$HDRF" || echo "  (başlık yok — TRIBE_SAVE_OUTPUTS=0 olabilir)"
rm -f "$HDRF"
echo "İçerik: unzip -l \"$OUT\""
