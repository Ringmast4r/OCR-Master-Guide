<#
.SYNOPSIS
  OCR Master Guide: Windows install. Tesseract 5.5 (UB Mannheim) + tessdata_best + Python venv + CPU stack.

.USAGE
  .\scripts\install-windows.ps1            # CPU stack
  .\scripts\install-windows.ps1 -Gpu       # + PyTorch CUDA 12.6 wheel + GPU requirements (EasyOCR, PaddleOCR, Surya, Marker, Docling)
  .\scripts\install-windows.ps1 -Full      # + Ghostscript, Poppler, ImageMagick, PowerToys, Ollama via winget

  Run from the repo root. Re-runnable. Needs winget and the Python launcher (py) with 3.11 or 3.12.
#>
param([switch]$Gpu, [switch]$Full)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
Write-Host "== OCR Master Guide: Windows install ==" -ForegroundColor Cyan

# 1. Tesseract
$tess = "C:\Program Files\Tesseract-OCR"
if (-not (Test-Path "$tess\tesseract.exe")) {
    Write-Host "-- installing Tesseract (UB Mannheim) via winget"
    winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
} else {
    Write-Host "-- Tesseract present: $(& "$tess\tesseract.exe" --version 2>&1 | Select-Object -First 1)"
    Write-Host "   (to upgrade: winget upgrade UB-Mannheim.TesseractOCR)"
}
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$tess*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$tess", "User")
    Write-Host "-- added $tess to user PATH (open a new terminal for it to apply)"
}
$env:Path = "$env:Path;$tess"

# 2. tessdata_best: eng, osd, script/Latin. Try Program Files, fall back to a user folder.
$td = "$tess\tessdata"
$files = @(
    @{ url = "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata"; rel = "eng.traineddata" },
    @{ url = "https://github.com/tesseract-ocr/tessdata_best/raw/main/osd.traineddata"; rel = "osd.traineddata" },
    @{ url = "https://github.com/tesseract-ocr/tessdata_best/raw/main/script/Latin.traineddata"; rel = "script\Latin.traineddata" }
)
try {
    New-Item -ItemType Directory -Force "$td\script" | Out-Null
    foreach ($f in $files) {
        Write-Host "-- downloading tessdata_best/$($f.rel)"
        Invoke-WebRequest -Uri $f.url -OutFile (Join-Path $td $f.rel) -UseBasicParsing
    }
    [Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", $td, "User")
} catch {
    $td = Join-Path $env:LOCALAPPDATA "tessdata_best"
    Write-Host "-- no write access to Program Files; using $td (TESSDATA_PREFIX points there)"
    New-Item -ItemType Directory -Force "$td\script" | Out-Null
    foreach ($f in $files) {
        Invoke-WebRequest -Uri $f.url -OutFile (Join-Path $td $f.rel) -UseBasicParsing
    }
    Copy-Item "$tess\tessdata\*.traineddata" $td -ErrorAction SilentlyContinue
    [Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", $td, "User")
}
$env:TESSDATA_PREFIX = $td

# 3. Python venv (3.11 or 3.12; the 3.14 alpha has no wheels)
$py = $null
foreach ($v in @("-3.12", "-3.11")) {
    try { & py $v --version *> $null; if ($LASTEXITCODE -eq 0) { $py = $v; break } } catch {}
}
if (-not $py) { throw "Need Python 3.11 or 3.12 via the py launcher: winget install Python.Python.3.12" }
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "-- creating .venv with py $py"
    & py $py -m venv .venv
}
$pip = ".\.venv\Scripts\python.exe"
& $pip -m pip install -U pip wheel
Write-Host "-- installing CPU requirements"
& $pip -m pip install -r scripts\requirements.txt

# 4. GPU stack
if ($Gpu) {
    Write-Host "-- installing PyTorch CUDA 12.6 wheel (check https://pytorch.org for the current index if this fails)"
    & $pip -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
    Write-Host "-- installing GPU requirements"
    & $pip -m pip install -r scripts\requirements-gpu.txt
    & $pip -c "import torch; print('cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
}

# 5. Optional helpers
if ($Full) {
    foreach ($id in @("ArtifexSoftware.GhostScript", "oschwartz10612.Poppler", "ImageMagick.ImageMagick", "Microsoft.PowerToys", "Ollama.Ollama", "7zip.7zip")) {
        Write-Host "-- winget install $id"
        winget install --id $id -e --accept-package-agreements --accept-source-agreements
    }
}

# 6. Verify
Write-Host "`n== verify ==" -ForegroundColor Cyan
& "$tess\tesseract.exe" --version 2>&1 | Select-Object -First 1
& "$tess\tesseract.exe" --list-langs 2>&1
& $pip scripts\ocr_bench.py --list
Write-Host "`nNext:  .\.venv\Scripts\Activate.ps1 ; python scripts\ocr_bench.py samples\clean_300dpi.png --gt samples\ground_truth.txt" -ForegroundColor Green
