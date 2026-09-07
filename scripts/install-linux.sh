#!/usr/bin/env bash
# OCR Master Guide: Linux install. Tesseract + OCRmyPDF + unpaper + Python venv + CPU stack.
#
#   bash scripts/install-linux.sh          # CPU stack
#   bash scripts/install-linux.sh --gpu    # + PyTorch CUDA 12.6 wheel + GPU requirements
#
# Debian/Ubuntu, Fedora, Arch. Re-runnable. Run from the repo root (or anywhere; it cds).
set -euo pipefail
cd "$(dirname "$0")/.."
GPU=0; [[ "${1:-}" == "--gpu" ]] && GPU=1
echo "== OCR Master Guide: Linux install =="

SUDO=""; [[ $EUID -ne 0 ]] && SUDO="sudo"
if command -v apt-get >/dev/null; then
  $SUDO apt-get update
  $SUDO apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd tesseract-ocr-script-latn \
      libtesseract-dev libleptonica-dev ocrmypdf unpaper ghostscript qpdf poppler-utils img2pdf pngquant \
      imagemagick python3-venv python3-dev build-essential curl
  TD=/usr/share/tesseract-ocr/5/tessdata; [[ -d $TD ]] || TD=/usr/share/tesseract-ocr/4.00/tessdata
elif command -v dnf >/dev/null; then
  $SUDO dnf install -y tesseract tesseract-langpack-eng tesseract-osd tesseract-devel leptonica-devel \
      ocrmypdf unpaper ghostscript qpdf poppler-utils ImageMagick python3 python3-devel gcc curl
  TD=/usr/share/tesseract/tessdata; [[ -d $TD ]] || TD=/usr/share/tessdata
elif command -v pacman >/dev/null; then
  $SUDO pacman -Sy --noconfirm tesseract tesseract-data-eng tesseract-data-osd ocrmypdf unpaper ghostscript qpdf \
      poppler imagemagick python base-devel curl
  TD=/usr/share/tessdata
else
  echo "unsupported package manager; install tesseract, ocrmypdf, unpaper, ghostscript, qpdf, poppler by hand"; exit 1
fi

# tessdata_best overlay (eng, osd, script/Latin)
echo "-- tessdata_best into $TD"
$SUDO mkdir -p "$TD/script"
for f in eng.traineddata osd.traineddata script/Latin.traineddata; do
  $SUDO curl -fsSL -o "$TD/$f" "https://github.com/tesseract-ocr/tessdata_best/raw/main/$f"
done

# venv
PY=python3
for c in python3.12 python3.11; do command -v $c >/dev/null && PY=$c && break; done
[[ -x .venv/bin/python ]] || $PY -m venv .venv
.venv/bin/python -m pip install -U pip wheel
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python -m pip install tesserocr || echo "tesserocr build skipped (needs libtesseract-dev); pytesseract still works"

if [[ $GPU -eq 1 ]]; then
  .venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
  .venv/bin/python -m pip install -r scripts/requirements-gpu.txt
  .venv/bin/python -m pip install onnxruntime-gpu
  .venv/bin/python -c "import torch; print('cuda:', torch.cuda.is_available())"
fi

echo; echo "== verify =="
tesseract --version | head -1
tesseract --list-langs
ocrmypdf --version
.venv/bin/python scripts/ocr_bench.py --list
echo; echo "Next:  source .venv/bin/activate ; python scripts/ocr_bench.py samples/noisy_skewed.png --gt samples/ground_truth.txt"
