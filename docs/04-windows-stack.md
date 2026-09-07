# 04. Windows stack

[Back to README](../README.md) | Prev: [Tesseract deep dive](03-tesseract-deep-dive.md) | Next: [Linux stack](05-linux-stack.md)

Everything here was checked on Windows 10 Home 19045 with an RTX 3070. Windows 11 notes are marked.
The short version: Windows is a first-class OCR platform in 2026. Two engines ship with the OS, Tesseract
has a maintained installer, every PyTorch/ONNX engine has Windows wheels, and the few Linux-only pieces
(vLLM, unpaper, olmOCR's pipeline) run in WSL2 with GPU passthrough.

`scripts/install-windows.ps1` does sections 1, 2, and 5 for you.

---

## 1. Tesseract on Windows

```powershell
# Install (UB Mannheim build, 64-bit, tracks upstream releases within days)
winget install --id UB-Mannheim.TesseractOCR -e
# or: choco install tesseract
# or the installer: https://github.com/UB-Mannheim/tesseract/wiki  (tesseract-ocr-w64-setup-5.5.3.20260724.exe)

# It lands in C:\Program Files\Tesseract-OCR and is NOT added to PATH by default. Fix that for your user:
$p = "C:\Program Files\Tesseract-OCR"
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";$p", "User")
[Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", "$p\tessdata", "User")
# open a new terminal, then:
tesseract --version
tesseract --list-langs
```

The installer's language picker pulls from `tessdata_fast`. For accuracy, drop `tessdata_best` files on top:

```powershell
$td = "C:\Program Files\Tesseract-OCR\tessdata"
Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata -OutFile "$td\eng.traineddata"
Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_best/raw/main/osd.traineddata -OutFile "$td\osd.traineddata"
New-Item -ItemType Directory -Force "$td\script" | Out-Null
Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_best/raw/main/script/Latin.traineddata -OutFile "$td\script\Latin.traineddata"
```

(Writing into Program Files needs an elevated shell. Alternative: keep a `tessdata_best` folder under your user
profile and pass `--tessdata-dir`, or point `TESSDATA_PREFIX` at it.)

Upgrading from an older installer (this machine had 5.4.0): run the new installer over it; it keeps `tessdata`.

---

## 2. Python on Windows: which interpreter

Use **Python 3.11 or 3.12**. On this box `py -3.11` is 3.11.9 and the default `python` is a 3.14 alpha with no
binary wheels for PaddlePaddle, PyTorch, or onnxruntime. Every recipe uses:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip wheel
pip install -r scripts\requirements.txt          # CPU stack
```

If `Activate.ps1` is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Long path issues with PaddleOCR and torch: enable long paths once
(`New-ItemProperty -Path HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force`, admin).

---

## 3. The two engines already inside Windows

### 3a. Windows.Media.Ocr (Windows 10 and 11)

The WinRT OCR API. Used by PowerToys Text Extractor, OneNote, and a lot of apps. Word bounding boxes, no
confidences, fast, handles rendered/anti-aliased text well. Languages are OS language packs:
Settings > Time and Language > Language > Add a language > check "Optical character recognition" under the
language's options. Or from an admin PowerShell:

```powershell
Get-WindowsCapability -Online | Where-Object Name -like "Language.OCR*"
Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
```

From Python, [winocr](https://pypi.org/project/winocr/) wraps it:

```powershell
pip install winocr
```

```python
import winocr
from PIL import Image
img = Image.open("screenshot.png")
res = winocr.recognize_pil_sync(img, "en")
print(res["text"])
for line in res["lines"]:
    for w in line["words"]:
        print(w["text"], w["bounding_rect"])
```

`winocr` also has a tiny HTTP server mode (`winocr_serve`) so Linux boxes on your LAN can post images to a
Windows machine and get JSON back.

From PowerShell directly (no Python):

```powershell
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
# (full script: see scripts/windows_native_ocr.py for the Python path; the PowerShell WinRT async dance is in the
#  isladogs.co.uk "copy text anywhere" write-up linked in docs/13-link-index.md)
```

### 3b. OneOCR (the Snipping Tool engine, Windows 11; usable on 10 with copied files)

Windows 11's Snipping Tool "Text actions", the Photos app, and Phone Link use a newer ONNX-based engine called
OneOCR. It is measurably better than Windows.Media.Ocr on small fonts and mixed layouts and returns
word confidences and text angle. It lives in three files inside the Snipping Tool package:

```
oneocr.dll
oneocr.onemodel      (encrypted bundle of 34 ONNX models)
onnxruntime.dll
```

Python wrapper: [AuroraWright/oneocr](https://github.com/AuroraWright/oneocr) (`pip install oneocr`). The readme
explains how to fetch the `Microsoft.ScreenSketch` msixbundle via store.rg-adguard.net (search
`https://apps.microsoft.com/detail/9mz95kl8mr0l`), extract it with 7-Zip, and copy the three files next to your
script or into `%USERPROFILE%\.config\oneocr`. On Windows 11 they are already on disk under
`C:\Program Files\WindowsApps\Microsoft.ScreenSketch_*\SnippingTool\` (protected folder; copy from an admin shell).

```python
import oneocr
from PIL import Image
engine = oneocr.OcrEngine()
r = engine.recognize_pil(Image.open("ui.png"))
print(r["text"], r["text_angle"])
for line in r["lines"]:
    for w in line["words"]:
        print(w["text"], round(w["confidence"], 2), w["bounding_rect"])
```

Related: [b1tg/win11-oneocr](https://github.com/b1tg/win11-oneocr) and [hawkhai/win11-oneocr](https://github.com/hawkhai/win11-oneocr)
(C and C# callers), and [MattyMroz/oneocr](https://huggingface.co/MattyMroz/oneocr), a reimplementation that
decrypted `.onemodel`, extracted the ONNX graphs, and runs them on any OS with onnxruntime. Licensing of those
model files is Microsoft's, so treat that as a research curiosity, not a product dependency.

### 3c. PowerToys Text Extractor

`winget install Microsoft.PowerToys`. Win+Shift+T, drag, paste. It uses the Windows.Media.Ocr languages, so install
the OCR capability for every language you read. Settings let you pick the preferred language and a table-mode
toggle that preserves column spacing. This is the fastest "I just need that error message as text" tool on Windows.

### 3d. Other native-ish tools

| Tool | Notes |
|:-----|:------|
| Snipping Tool text actions (Win 11) | OneOCR. Also redacts emails/phones. |
| OneNote | Right-click a pasted image, "Copy Text from Picture". Slow but handles multi-page printouts. |
| ShareX | After-capture OCR action; uses Windows OCR. |
| NormCap | `winget install dynobo.NormCap`, bundles Tesseract, works the same as on Linux. |
| gImageReader | Windows builds on the releases page; batch OCR with a GUI and hOCR editing. |
| Capture2Text | Old Tesseract hotkey tool; superseded by PowerToys. |
| ABBYY FineReader PDF | Still the best commercial desktop OCR on Windows. |

---

## 4. GPU on Windows (RTX 3070, 8 GB)

You do not need the CUDA toolkit. PyTorch and onnxruntime-gpu wheels bundle the CUDA runtime; the NVIDIA driver
(610.88 on this box) is enough.

```powershell
# PyTorch with CUDA 12.x (pick the index that matches the current torch release page)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# ONNX Runtime GPU (RapidOCR, OnnxTR, docTR-onnx use it)
pip install onnxruntime-gpu

# PaddlePaddle GPU (PaddleOCR). Baidu's index; check https://www.paddlepaddle.org.cn for the current cu12x tag
pip install paddlepaddle-gpu==3.* -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
pip install paddleocr
```

What runs natively on Windows with the GPU: PaddleOCR, RapidOCR (onnxruntime-gpu), EasyOCR, docTR, Surya,
Marker, MinerU (`pipeline` backend, and the `vlm` backend via Transformers), Docling, TrOCR, pix2tex, Nougat,
any Hugging Face Transformers model (PaddleOCR-VL, DeepSeek-OCR, dots.ocr, LightOnOCR, Granite-Docling, GOT-OCR),
and Ollama (Qwen3-VL, MiniCPM-V, Gemma 3).

What does **not** run natively: **vLLM** and **SGLang** (the fast batched servers), `unpaper`, olmOCR's pipeline,
Kraken (technically installs, practically painful). Those go in WSL2.

VRAM fit table for the 8 GB card: [07-vlm-document-parsers.md](07-vlm-document-parsers.md#vram-fit-table-8-gb-card).

---

## 5. WSL2 with GPU passthrough

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

Inside Ubuntu the NVIDIA driver is already visible (`nvidia-smi` works). Do **not** install a Linux NVIDIA driver
inside WSL. Install the CUDA-enabled wheels as on Linux. Then follow [05-linux-stack.md](05-linux-stack.md) verbatim:
`apt install tesseract-ocr ocrmypdf unpaper`, `pip install vllm`, `pip install olmocr[gpu]`.

Files: `/mnt/e/...` reaches the E: drive but is slow for thousands of small images; copy batches into the WSL
filesystem (`~/work`) first, or use `\\wsl$\Ubuntu-24.04\home\...` from Windows.

Docker Desktop with the WSL2 backend gives you `docker run --gpus all vllm/vllm-openai` on Windows.

---

## 6. Ollama on Windows (the easiest VLM route)

```powershell
winget install Ollama.Ollama
ollama pull qwen3-vl:8b          # about 6 GB at q4, fits the 3070
ollama run qwen3-vl:8b "Transcribe every word in this image exactly, preserving line breaks. ./page.png"
```

Python:

```python
import ollama
r = ollama.chat(model="qwen3-vl:8b", messages=[{
    "role": "user",
    "content": "Transcribe this page to Markdown. Keep tables as Markdown tables. Do not summarize or correct spelling.",
    "images": ["page.png"]}])
print(r["message"]["content"])
```

Ollama on Windows uses the GPU automatically. For a proper document parser rather than a chat model, use
PaddleOCR-VL or DeepSeek-OCR through Transformers (see [07](07-vlm-document-parsers.md)); for batch throughput,
vLLM in WSL2.

---

## 7. PDF plumbing on Windows

| Need | Install |
|:-----|:--------|
| Rasterize PDFs | `pip install pymupdf` (no external binary) or `pip install pypdfium2` |
| Poppler (`pdftoppm`, for pdf2image) | `winget install oschwartz10612.Poppler` then add `Library\bin` to PATH |
| Ghostscript (OCRmyPDF) | `winget install ArtifexSoftware.GhostScript` |
| qpdf | `winget install QPDF.QPDF` or `pip install pikepdf` (bundles it) |
| ImageMagick | `winget install ImageMagick.ImageMagick` |
| OCRmyPDF | `pip install ocrmypdf` after Tesseract + Ghostscript; `--clean` is unavailable (unpaper is Linux only) |
| 7-Zip (for msixbundles) | `winget install 7zip.7zip` |

---

## 8. A minimal Windows-native pipeline (no Python)

```powershell
# 1. Screenshot -> text: Win+Shift+T (PowerToys)
# 2. Scanned PDF -> searchable PDF:
ocrmypdf --deskew --rotate-pages --skip-text -l eng --jobs 8 in.pdf out.pdf
# 3. Folder of images -> one text file:
Get-ChildItem *.png | ForEach-Object { tesseract $_.FullName stdout --psm 6 } | Out-File -Encoding utf8 all.txt
# 4. Rotate detection:
tesseract page.png stdout --psm 0 -l osd
```

---

## 9. Troubleshooting

| Symptom | Fix |
|:--------|:----|
| `tesseract is not recognized` | Not on PATH. Section 1, or set `pytesseract.pytesseract.tesseract_cmd`. |
| `Error opening data file ... eng.traineddata` | `TESSDATA_PREFIX` wrong. It must point at the folder that contains the `.traineddata` files. |
| Empty output on a screenshot | Upscale 2x to 3x and use `--psm 6`. Or just use OneOCR. |
| `paddlepaddle` import crashes | Wrong Python (3.14 alpha) or wrong CUDA wheel. Use `py -3.11` and the CPU wheel first. |
| `torch.cuda.is_available()` is False | Installed the CPU wheel. Reinstall with the `--index-url .../cu126` line. |
| `winocr` returns nothing | Language OCR capability not installed. Section 3a. |
| `oneocr` cannot find dll | Copy the three files next to the script or to `%USERPROFILE%\.config\oneocr`. |
| vLLM `pip install` fails | Expected on Windows. WSL2. |
| Long path errors during pip | Enable `LongPathsEnabled` (section 2). |
| Surya/Marker slow | They are running on CPU. Install the CUDA torch wheel first, then reinstall them. |
