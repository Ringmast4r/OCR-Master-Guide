<#
.SYNOPSIS
  OCR Master Guide: install the leaderboard winners that fit an 8 GB GPU, natively on Windows.

  PaddleOCR-VL 1.6   rank 1 OmniDocBench  (Baidu, 0.9B)         via paddlepaddle-gpu + paddleocr[doc-parser]
  MinerU 2.5         rank 2 OmniDocBench  (OpenDataLab, 1.2B)   via mineru[core], vlm-transformers backend
  Marker + Surya 2   rank 5 olmOCR-Bench  (Datalab)             via marker-pdf, surya-ocr
  Docling            IBM/Linux Foundation pipeline              via docling
  Transformers       runs GLM-OCR, DeepSeek-OCR, dots.ocr, Chandra (4-bit), Nanonets-OCR2, LightOnOCR from Hugging Face
  RapidOCR, pytesseract, winocr   CPU engines for the diff (recipe 13)

.USAGE
  .\scripts\install-best.ps1                 # everything above into .\.venv (Python 3.11/3.12 via py launcher)
  .\scripts\install-best.ps1 -Cuda cu126     # pick the torch/paddle CUDA tag (default cu126; cu118 for old drivers)
  .\scripts\install-best.ps1 -SkipMinerU     # skip the AGPL one

  ~6 GB of downloads. Re-runnable. Tesseract itself: run install-windows.ps1 (winget) or skip it.
#>
param([string]$Cuda = "cu126", [switch]$SkipMinerU, [switch]$SkipMarker)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
Write-Host "== OCR Master Guide: install the best ($Cuda) ==" -ForegroundColor Cyan

# Python 3.11 / 3.12
$py = $null
foreach ($v in @("-3.12", "-3.11")) {
    try { & py $v --version *> $null; if ($LASTEXITCODE -eq 0) { $py = $v; break } } catch {}
}
if (-not $py) { throw "Need Python 3.11 or 3.12 via the py launcher: winget install Python.Python.3.12" }
if (-not (Test-Path ".venv\Scripts\python.exe")) { & py $py -m venv .venv }
$pip = ".\.venv\Scripts\python.exe"
& $pip -m pip install -U pip wheel

# 1. PyTorch CUDA (Marker, Surya, Docling, Transformers models, MinerU vlm backend)
Write-Host "-- torch $Cuda" -ForegroundColor Cyan
& $pip -m pip install torch torchvision --index-url "https://download.pytorch.org/whl/$Cuda"

# 2. PaddlePaddle GPU + PaddleOCR-VL (rank 1)
Write-Host "-- paddlepaddle-gpu $Cuda + paddleocr[doc-parser]" -ForegroundColor Cyan
& $pip -m pip install "paddlepaddle-gpu==3.2.1" -i "https://www.paddlepaddle.org.cn/packages/stable/$Cuda/"
& $pip -m pip install -U "paddleocr[doc-parser]"

# 3. CPU engines + eval tools
Write-Host "-- CPU stack (rapidocr, pytesseract, winocr, jiwer, opencv, pymupdf)" -ForegroundColor Cyan
& $pip -m pip install -r scripts\requirements.txt

# 4. Marker + Surya 2 + Docling + Transformers
if (-not $SkipMarker) {
    Write-Host "-- marker-pdf, surya-ocr, docling, transformers, accelerate, bitsandbytes" -ForegroundColor Cyan
    & $pip -m pip install marker-pdf surya-ocr docling transformers accelerate bitsandbytes
}

# 5. MinerU 2.5 (AGPL-3.0)
if (-not $SkipMinerU) {
    Write-Host "-- mineru[core]" -ForegroundColor Cyan
    & $pip -m pip install -U "mineru[core]"
}

# 6. Verify
Write-Host "`n== verify ==" -ForegroundColor Cyan
& $pip -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
& $pip -c "import paddle; print('paddle', paddle.__version__, 'gpu', paddle.device.is_compiled_with_cuda())"
& $pip -c "import paddleocr; print('paddleocr', paddleocr.__version__)"
& $pip scripts\ocr_bench.py --list
Write-Host "`nRank 1 model, first run downloads PaddleOCR-VL-1.6:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  paddleocr doc_parser -i samples\clean_300dpi.png --save_path out\"
Write-Host "  mineru -p some.pdf -o out\ -b vlm-transformers"
Write-Host "  marker_single some.pdf --output_dir out\"
