# 05. Linux stack

[Back to README](../README.md) | Prev: [Windows stack](04-windows-stack.md) | Next: [Pairing recipes](06-pairing-recipes.md)

Linux is where every OCR project is developed first. All the servers (vLLM, SGLang), all the batch tools
(olmOCR, OCR-D), and all the cleanup utilities (unpaper) are native. `scripts/install-linux.sh` does
sections 1 and 3.

---

## 1. Distro packages

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd tesseract-ocr-script-latn \
    libtesseract-dev libleptonica-dev \
    ocrmypdf unpaper ghostscript qpdf poppler-utils img2pdf pngquant jbig2enc \
    imagemagick python3-venv python3-dev build-essential

# Fedora
sudo dnf install -y tesseract tesseract-langpack-eng tesseract-osd ocrmypdf unpaper ghostscript qpdf poppler-utils ImageMagick

# Arch
sudo pacman -S tesseract tesseract-data-eng tesseract-data-osd ocrmypdf unpaper ghostscript qpdf poppler imagemagick

# Where the models went
tesseract --list-langs
ls /usr/share/tesseract-ocr/5/tessdata/    # Debian/Ubuntu
ls /usr/share/tessdata/                    # Fedora/Arch
```

Distro models are `tessdata_fast`. Overlay `tessdata_best` for measured work:

```bash
TD=/usr/share/tesseract-ocr/5/tessdata
sudo curl -L -o $TD/eng.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata
sudo mkdir -p $TD/script && sudo curl -L -o $TD/script/Latin.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/script/Latin.traineddata
```

Building Tesseract from source (for the newest release or training tools): the
[tessdoc compilation page](https://tesseract-ocr.github.io/tessdoc/Compiling.html). On Ubuntu it is
`autogen.sh && ./configure && make -j && sudo make install && make training && sudo make training-install`.

---

## 2. OCRmyPDF 17 (the Linux workhorse)

Version 17.0 (Jan 2026) was a major release; 17.4.1 (Apr 2026) is current. Notable in 17.x: right-to-left
text extraction fixed for Arabic and Hebrew, better Ghostscript JPEG-corruption detection, Python 3.10+.

```bash
# Everyday archive job
ocrmypdf --deskew --rotate-pages --clean --clean-final --optimize 3 --skip-text \
    -l eng --jobs $(nproc) --output-type pdfa --sidecar out.txt in.pdf out.pdf

# Replace an existing bad OCR layer
ocrmypdf --redo-ocr -l eng+deu in.pdf out.pdf

# Force rasterize a "born digital" PDF with broken fonts
ocrmypdf --force-ocr in.pdf out.pdf

# Watch a folder (poor man's Paperless)
pip install "ocrmypdf[watcher]" && ocrmypdf-watcher     # or just use Paperless-ngx

# Whole folder in parallel with GNU parallel
parallel --bar -j 4 ocrmypdf --skip-text -l eng {} out/{/} ::: in/*.pdf
```

**Plugins** let OCRmyPDF drive a different engine while keeping its PDF plumbing:
[ocrmypdf-easyocr](https://github.com/ocrmypdf/OCRmyPDF-EasyOCR) (official, experimental, GPU) and
community PaddleOCR/RapidOCR plugins on PyPI. The plugin API is documented at
[ocrmypdf.readthedocs.io/en/latest/plugins.html](https://ocrmypdf.readthedocs.io/en/latest/plugins.html).

Docker: `docker run --rm -i jbarlow83/ocrmypdf --skip-text - - < in.pdf > out.pdf`.

---

## 3. Python stack

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -r scripts/requirements.txt              # tesseract wrappers, rapidocr, doctr, ocrmypdf, jiwer, opencv

# GPU
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r scripts/requirements-gpu.txt          # easyocr, paddleocr, surya, marker, docling, transformers
pip install onnxruntime-gpu
pip install paddlepaddle-gpu==3.* -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

# tesserocr on Linux is a normal build against libtesseract-dev
pip install tesserocr
```

AMD: PyTorch ROCm wheels (`--index-url https://download.pytorch.org/whl/rocm6.x`) run EasyOCR, docTR, Surya,
Transformers models. PaddlePaddle ROCm support is limited; use RapidOCR on CPU or OpenVINO instead.
Intel: RapidOCR's `openvino` backend (`pip install rapidocr openvino`) is the fast CPU/iGPU path.

---

## 4. Desktop and screen OCR on Linux

| App | Install | Notes |
|:----|:--------|:------|
| [NormCap](https://github.com/dynobo/normcap) | `pipx install normcap` or the AppImage/Flatpak | Select a region, text in clipboard; Wayland and X11; detects URLs/emails; bundles Tesseract |
| [Frog](https://github.com/TenderOwl/Frog) | `flatpak install flathub com.github.tenderowl.frog` | GNOME; screen, video, QR |
| [gImageReader](https://github.com/manisandro/gImageReader) | `apt install gimagereader` / Flatpak | Batch scans, hOCR editor, PDF export |
| [OCRFeeder](https://gitlab.gnome.org/GNOME/ocrfeeder) | `apt install ocrfeeder` | Layout-aware, exports ODT |
| [Paperwork](https://openpaper.work/) | `apt install paperwork-gtk` | Personal document manager with OCR |
| [Paperless-ngx](https://docs.paperless-ngx.com/) | Docker compose | The real document management system: consume folder, OCRmyPDF, tags, full-text search, mobile apps |
| [ScanTailor Advanced](https://github.com/ScanTailor-Advanced/scantailor-advanced) | AppImage / distro | Book-scan post-processing before OCR |
| [Simple Scan / Document Scanner](https://gitlab.gnome.org/GNOME/simple-scan) | GNOME default | Scanning only; pair with OCRmyPDF |
| [eScriptorium](https://gitlab.com/scripta/escriptorium) | Docker compose | Transcribe and train Kraken models in the browser |
| [OCR4all](https://github.com/OCR4all/OCR4all) | Docker | Guided workflow for early printed books |

Screen OCR one-liner without any app (X11 or Wayland via `grim`/`slurp`):

```bash
# X11
maim -s | tesseract stdin stdout --psm 6 | xclip -selection clipboard
# Wayland (sway/hyprland)
grim -g "$(slurp)" - | tesseract stdin stdout --psm 6 | wl-copy
```

---

## 5. Servers: vLLM and SGLang (VLM OCR at throughput)

```bash
pip install vllm
# Serve a document model with an OpenAI-compatible API
vllm serve PaddlePaddle/PaddleOCR-VL --port 8000 --max-model-len 16384 --gpu-memory-utilization 0.90
vllm serve deepseek-ai/DeepSeek-OCR-2 --port 8000 --trust-remote-code
vllm serve datalab-to/chandra --port 8000            # needs 16 GB+; use the quantized build on 8 GB
```

Then any OpenAI client posts `{"model": ..., "messages": [{"role":"user","content":[{"type":"image_url",...},{"type":"text","text":"..."}]}]}`.
Every model in [07](07-vlm-document-parsers.md) has a vLLM recipe page at
[recipes.vllm.ai](https://recipes.vllm.ai/).

Docker: `docker run --gpus all -p 8000:8000 vllm/vllm-openai --model PaddlePaddle/PaddleOCR-VL`.

olmOCR (batch PDFs to Markdown, uses vLLM internally):

```bash
pip install "olmocr[gpu]" --extra-index-url https://download.pytorch.org/whl/cu128
python -m olmocr.pipeline ./workspace --markdown --pdfs ./pdfs/*.pdf
# or Docker: alleninstituteforai/olmocr
```

---

## 6. Historical and humanities stack

```bash
pip install kraken
kraken list                                  # models published to Zenodo's ocr_models community
kraken get 10.5281/zenodo.10592716           # example DOI; browse https://zenodo.org/communities/ocr_models
kraken -i page.png out.txt segment -bl ocr -m model.mlmodel
kraken -i page.png out.xml -a segment -bl ocr -m model.mlmodel    # ALTO out
ketos train -f page -o mymodel data/*.xml    # train on PAGE-XML ground truth
```

OCR-D: `pip install ocrd ocrd_tesserocr ocrd_calamari ocrd_kraken ocrd_anybaseocr` and drive a workflow with
`ocrd process`. The [OCR-D quick start](https://ocr-d.de/en/quick-start) covers METS/ALTO workspaces.

---

## 7. Docker images worth knowing

| Image | What |
|:------|:-----|
| `jbarlow83/ocrmypdf` | OCRmyPDF with every dependency |
| `paddlepaddle/paddle:*-gpu-cuda12*` | PaddlePaddle base; add `pip install paddleocr` |
| `vllm/vllm-openai` | vLLM server |
| `ollama/ollama` | Ollama with `--gpus all` |
| `ghcr.io/docling-project/docling-serve` | Docling as an HTTP service |
| `alleninstituteforai/olmocr` | olmOCR pipeline |
| `ghcr.io/paperless-ngx/paperless-ngx` | Paperless-ngx |
| `registry.gitlab.com/scripta/escriptorium` | eScriptorium |
| `ocrd/all` | Every OCR-D processor in one image |
| `luminainc/chunkr` | Chunkr ingestion API |

---

## 8. Troubleshooting

| Symptom | Fix |
|:--------|:----|
| `TesseractNotFoundError` in pytesseract | `apt install tesseract-ocr`; check `which tesseract` |
| `Failed loading language 'eng'` | `apt install tesseract-ocr-eng` or set `TESSDATA_PREFIX` |
| OCRmyPDF `--clean` error | `apt install unpaper` |
| OCRmyPDF `PriorOcrFoundError` | Add `--skip-text` or `--redo-ocr` |
| OCRmyPDF `EncryptedPdfError` | `qpdf --decrypt in.pdf tmp.pdf` first |
| ImageMagick refuses PDFs | Edit `/etc/ImageMagick-6/policy.xml`, change PDF `rights="none"` to `read\|write` |
| CUDA out of memory in vLLM | Lower `--max-model-len`, `--gpu-memory-utilization 0.8`, or a quantized model |
| `libGL.so.1` missing for OpenCV in Docker | `apt install libgl1` or use `opencv-python-headless` |
| PaddleOCR downloads models every run | Set `PADDLE_PDX_CACHE_HOME` or mount `~/.paddlex` |
