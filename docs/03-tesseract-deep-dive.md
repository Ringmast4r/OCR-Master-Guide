# 03. Tesseract deep dive

[Back to README](../README.md) | Prev: [Engine atlas](02-engine-atlas.md) | Next: [Windows stack](04-windows-stack.md)

You already run Tesseract. This guide is about running it *well*, because most Tesseract complaints are
configuration problems: wrong DPI, wrong model set, wrong page segmentation mode, dictionaries fighting
the input. Then it covers everything around it: output formats, wrappers, and fine-tuning.

---

## Versions and where they come from

| Item | Current | Notes |
|:-----|:--------|:------|
| Tesseract | **5.5.3** (24 Jul 2026) | [Releases](https://github.com/tesseract-ocr/tesseract/releases). 5.x is the LSTM engine with legacy optional. |
| Windows binaries | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) `tesseract-ocr-w64-setup-5.5.3.20260724.exe` | The canonical prebuilt. `winget install UB-Mannheim.TesseractOCR` or `choco install tesseract`. |
| Linux packages | Debian/Ubuntu `tesseract-ocr` (5.3 to 5.5 depending on release), Fedora `tesseract`, Arch `tesseract` | Distro packages ship `tessdata_fast` models. |
| Leptonica | 1.84+ | The image library. Binarization, deskew helpers, PDF rendering live here. |
| This machine | `v5.4.0.20240606` in `C:\Program Files\Tesseract-OCR`, not on PATH, `eng` + `osd` only | Upgrade. See [04](04-windows-stack.md). |

Release notes worth knowing: 5.0 (Nov 2021) made LSTM the default and dropped the old training tools;
5.3 added `--dpi` handling fixes and ALTO improvements; 5.4 improved PDF output and CJK spacing; 5.5 modernized
the build (C++17), improved `tesseract.exe` thread handling, and kept the same models. **Models did not change
between 4.0 and 5.5**; the accuracy gains you read about come from better preprocessing and from the
`tessdata_best` set, not from upgrading the binary.

---

## The three model repositories (this is the one everyone gets wrong)

| Repo | What is inside | Size (eng) | Speed | Accuracy | Fine-tunable | Use it when |
|:-----|:---------------|:----------:|:-----:|:--------:|:------------:|:------------|
| [tessdata](https://github.com/tesseract-ocr/tessdata) | LSTM **and** legacy models combined | 23 MB | medium | good | no | You need `--oem 0` or `--oem 2` (legacy engine) |
| [tessdata_best](https://github.com/tesseract-ocr/tessdata_best) | Float LSTM, the models training actually produced | 15 MB | slowest (about 2x fast) | **best** | **yes** (the only base for fine-tuning) | Accuracy matters, batch jobs, anything you will measure |
| [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) | Integer-quantized LSTM | 4 MB | fastest | slightly lower | no | Interactive tools, screenshots, distro defaults |

Language codes are ISO 639-2/T three-letter (`eng`, `deu`, `fra`, `spa`, `chi_sim`, `chi_tra`, `jpn`, `jpn_vert`,
`kor`, `ara`, `heb`, `rus`, `hin`, `ben`, `tha`, `vie`). Script models live under `script/` (`Latin`, `Cyrillic`,
`Arabic`, `Devanagari`, `HanS`, `HanT`, `Japanese`) and cover every language of that script in one file, which is
the better choice for mixed-language pages. `osd` is orientation and script detection. `equ` is the ancient math
model; do not use it.

```bash
# Where models live
tesseract --list-langs
tesseract --print-parameters | head

# Point at a different tessdata folder (points AT the folder holding *.traineddata)
export TESSDATA_PREFIX=/usr/share/tessdata          # Linux
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata"   # PowerShell
tesseract img.png out --tessdata-dir /path/to/tessdata_best -l eng
```

Download a model:

```bash
curl -L -o eng.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata
curl -L -o script/Latin.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/script/Latin.traineddata
```

---

## The command line

```
tesseract IMAGE OUTPUTBASE [options] [configfiles]
tesseract IMAGE stdout                         # print instead of writing OUTPUTBASE.txt
tesseract IMAGE out -l eng+deu                 # multiple languages (order = priority)
tesseract IMAGE out --psm 6 --oem 1            # segmentation + engine mode
tesseract IMAGE out --dpi 300                  # tell it the DPI if the image has no metadata
tesseract IMAGE out -c preserve_interword_spaces=1
tesseract IMAGE out txt hocr tsv pdf alto      # several outputs at once
tesseract list.txt out                         # list.txt = one image path per line, multipage output
tesseract IMAGE out --tessdata-dir DIR
tesseract --help-extra
```

### Page Segmentation Modes (`--psm`)

| PSM | Meaning | Use for |
|:---:|:--------|:--------|
| 0 | Orientation and script detection only | Deciding rotation before OCR (`-l osd`) |
| 1 | Auto segmentation with OSD | Unknown rotation, full pages |
| 3 | Fully automatic, no OSD (**default**) | Ordinary pages |
| 4 | Single column of variable-size text | Receipts, narrow columns, tables of text |
| 5 | Single uniform block of vertical text | Vertical CJK |
| 6 | Single uniform block of text | **Paragraph crops, screenshots of text, most "why is it blank" cases** |
| 7 | Single text line | Line crops, captchas, labels |
| 8 | Single word | Word crops |
| 9 | Single word in a circle | Coins, seals |
| 10 | Single character | Character classification |
| 11 | Sparse text, find as much as possible in no order | Forms, maps, scattered labels, UI |
| 12 | Sparse text with OSD | Same, unknown rotation |
| 13 | Raw line, no Tesseract hacks | Bypass segmentation entirely on a pre-cut line |

Rule of thumb: full page 3; a crop of a paragraph 6; a crop of a line 7; scattered labels 11.

### OCR Engine Modes (`--oem`)

| OEM | Engine | Needs |
|:---:|:-------|:------|
| 0 | Legacy only | combined `tessdata` models |
| 1 | LSTM only | any repo |
| 2 | Legacy + LSTM | combined `tessdata` |
| 3 | Default (LSTM if available) | any |

### Config variables (`-c name=value`, or a config file)

| Variable | Effect | When |
|:---------|:-------|:-----|
| `tessedit_char_whitelist=0123456789ABCDEF` | Restrict output alphabet (works with LSTM since 4.1) | Serials, hex, plates |
| `tessedit_char_blacklist=\|` | Forbid characters | Pipes read as l/I |
| `load_system_dawg=0` `load_freq_dawg=0` | Disable dictionaries | Codes, names, non-words |
| `preserve_interword_spaces=1` | Keep runs of spaces | Column-aligned text, receipts, code |
| `user_defined_dpi=300` | Assume DPI when metadata missing | Screenshots, cropped PNGs |
| `tessedit_do_invert=0` | Do not try inverted text | Speed on normal pages |
| `thresholding_method=2` | 0 Otsu (default), 1 LeptonicaOtsu, 2 Sauvola (5.x) | Uneven lighting |
| `textord_min_linesize=2.5` | Minimum line size heuristic | Tiny text |
| `tessedit_write_images=1` | Dump `tessinput.tif`, the image after internal preprocessing | Debugging binarization |
| `tessedit_create_hocr=1` etc. | Same as listing `hocr` on the CLI | Wrappers |
| `lstm_choice_mode=2` | Emit per-symbol alternatives in hOCR | Confidence tooling |
| `hocr_font_info=1` | Font attributes in hOCR (legacy engine only) | Rarely |
| `page_separator=` | Remove the form-feed between pages | Multi-page txt |

Config files are plain `name value` lines. Tesseract ships some: `tessconfigs/`, `configs/` (`hocr`, `tsv`, `pdf`,
`alto`, `digits`, `quiet`, `txt`, `get.images`). Pass by name: `tesseract img out digits`.

### Output formats

| Argument | File | Contains |
|:---------|:-----|:---------|
| `txt` (default) | `out.txt` | Plain text |
| `hocr` | `out.hocr` | HTML with `ocr_page/ocr_carea/ocr_par/ocr_line/ocrx_word`, `bbox`, `x_wconf` |
| `tsv` | `out.tsv` | `level page_num block_num par_num line_num word_num left top width height conf text` |
| `pdf` | `out.pdf` | Original image + invisible text layer (`pdf.ttf` is the glyphless font) |
| `alto` | `out.xml` | ALTO 4 |
| `page` | `out.page` | PAGE-XML (5.4+) |
| `lstmbox`, `wordstrbox` | box files | Training ground truth helpers |
| `-c textonly_pdf=1` with `pdf` | text-only PDF | For OCRmyPDF-style sandwiching |

The TSV is the format to use for review queues: filter `conf < 60`, draw the boxes, look.

---

## Getting the input right (80 percent of Tesseract accuracy)

1. **300 DPI, x-height 20+ px.** Rasterize PDFs at 300 (`pdftoppm -r 300`, PyMuPDF `page.get_pixmap(dpi=300)`).
   Upscale screenshots 2x to 3x with Lanczos. Do not go past about 600 DPI; it gets slower and worse.
2. **Deskew.** Tesseract tolerates about 1 degree. `unpaper`, ImageMagick `-deskew 40%`, or the OpenCV
   routine in [08](08-preprocessing.md).
3. **Binarize yourself when lighting is uneven.** Sauvola (scikit-image) or adaptive Gaussian (OpenCV), then
   feed the binary image. Set `tessedit_write_images=1` once to see what Tesseract would have done on its own.
4. **Crop to the text.** Borders, punch holes, scanner shadows create phantom text blocks. `unpaper` or a
   morphological border trim.
5. **Pick the PSM.** A screenshot of a paragraph with default PSM 3 often returns nothing; PSM 6 fixes it.
6. **Choose the model set.** `tessdata_best` for anything measured. Distro and UB Mannheim defaults are fast.
7. **Match the language.** Wrong language = wrong dictionary = wrong words. Mixed pages: `-l eng+deu` or the script model.
8. **Kill the dictionary** for codes, tables of numbers, hashes.

A cheap sanity test:

```bash
tesseract img.png stdout --psm 6 -c tessedit_write_images=1 && open tessinput.tif   # look at the binarized image
```

If `tessinput.tif` looks bad, no amount of PSM tweaking will save you; fix the image.

---

## Python wrappers

| Wrapper | How it works | Speed | Install | When |
|:--------|:-------------|:-----:|:--------|:-----|
| [pytesseract](https://github.com/madmaze/pytesseract) | Spawns `tesseract.exe` per call, parses output | slow per call (process spawn) | `pip install pytesseract` | Scripts, notebooks, anything under 1,000 images |
| [tesserocr](https://github.com/sirfz/tesserocr) | Direct C API binding (`PyTessBaseAPI`), keeps the engine loaded | fast, iterators for boxes/confidences | Linux: `pip install tesserocr` (needs libtesseract-dev). Windows: wheels from [simonflueckiger/tesserocr-windows_build](https://github.com/simonflueckiger/tesserocr-windows_build) or conda-forge | Services, loops, GetComponentImages |
| [OCRmyPDF](https://ocrmypdf.readthedocs.io/) | Orchestrates Tesseract per page with Ghostscript/qpdf/unpaper | parallel `--jobs` | `pip install ocrmypdf` | PDFs |
| [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html) | `page.get_textpage_ocr()` calls Tesseract, `Pixmap.pdfocr_save()` | fast | `pip install pymupdf` + TESSDATA_PREFIX | Mixed text/image PDFs |
| [Docling tesseract engine](https://docling-project.github.io/docling/concepts/OCR/) | `TesseractOcrOptions` / `TesseractCliOcrOptions` | n/a | `pip install docling` | Docling pipelines |

```python
# pytesseract, the right way
import pytesseract, cv2
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"   # Windows if not on PATH

img = cv2.imread("scan.png")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)          # if it came from a screen
bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

cfg = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
text = pytesseract.image_to_string(bw, lang="eng", config=cfg)
data = pytesseract.image_to_data(bw, lang="eng", config=cfg, output_type=pytesseract.Output.DATAFRAME)
low = data[(data.conf > -1) & (data.conf < 60)]           # review queue
hocr = pytesseract.image_to_pdf_or_hocr(bw, extension="hocr", lang="eng", config=cfg)
osd  = pytesseract.image_to_osd(img)                        # rotation + script, needs osd.traineddata
```

```python
# tesserocr, keep the engine hot
from tesserocr import PyTessBaseAPI, PSM, RIL
with PyTessBaseAPI(path=r"C:\Program Files\Tesseract-OCR\tessdata", lang="eng", psm=PSM.SINGLE_BLOCK) as api:
    for f in files:
        api.SetImageFile(f)
        print(api.GetUTF8Text(), api.MeanTextConf())
        boxes = api.GetComponentImages(RIL.TEXTLINE, True)
        for i, (im, box, _, _) in enumerate(boxes):
            api.SetRectangle(box["x"], box["y"], box["w"], box["h"])
            print(i, api.GetUTF8Text().strip(), api.MeanTextConf())
```

---

## Multi-page PDFs

```bash
# The tool you actually want
ocrmypdf --deskew --rotate-pages --clean --optimize 1 --skip-text -l eng --jobs 8 --sidecar out.txt in.pdf out.pdf

# By hand
pdftoppm -r 300 -png in.pdf page          # page-1.png ...
ls page-*.png > list.txt
tesseract list.txt out -l eng pdf txt     # multipage searchable PDF + text
```

OCRmyPDF flags that matter: `--skip-text` (leave pages with a text layer alone), `--force-ocr` (rasterize
everything), `--redo-ocr` (replace a bad existing OCR layer), `--output-type pdfa|pdf`, `--pdf-renderer hocr|sandwich`,
`--tesseract-timeout`, `--tesseract-pagesegmode 6`, `--tesseract-config file`, `--user-words`, `--user-patterns`,
`--clean` and `--clean-final` (unpaper, Linux/WSL), `--remove-background`, `--oversample 300`, `--threshold`,
`--jobs N`, `--plugin` (custom engines, see [05](05-linux-stack.md)).

---

## Fine-tuning Tesseract (when and how)

**When it is worth it:** one consistent typeface or hand that the stock model reads at 90 to 95 percent and
you need 99. Dot-matrix receipts, a specific ledger, a historical typeface, license plates, a proprietary
font. **When it is not:** general documents (use a better engine instead), fewer than 20 lines of ground truth,
or a Windows-only workflow with no WSL (the training tools want `make`).

**Rules:** fine-tune from `tessdata_best` only. Match the training tools to the installed Tesseract version.
The old `tesstrain.sh` script is gone; use the [tesstrain](https://github.com/tesseract-ocr/tesstrain) Makefile.

```bash
# Linux / WSL2. Install training tools (Debian: tesseract-ocr training tools are in the main package on 5.x)
sudo apt install tesseract-ocr libtesseract-dev git make wget bc python3
git clone https://github.com/tesseract-ocr/tesstrain && cd tesstrain
mkdir -p data/myfont-ground-truth
# Put line images + transcripts here: 0001.png + 0001.gt.txt, 0002.png + 0002.gt.txt ... (100+ lines is a good start)

# Fetch the base model you fine-tune from
make tesseract-langdata
wget -P data/ https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata

# Fine-tune. START_MODEL = base. MODEL_NAME = your new language code.
make training MODEL_NAME=myfont START_MODEL=eng TESSDATA=data MAX_ITERATIONS=3000 LEARNING_RATE=0.0001

# Result
ls data/myfont.traineddata
cp data/myfont.traineddata /usr/share/tesseract-ocr/5/tessdata/    # or your TESSDATA_PREFIX
tesseract test.png stdout -l myfont
```

What the Makefile runs underneath, so you can debug it:

```bash
combine_tessdata -e eng.traineddata eng.lstm                           # extract the LSTM from the base
text2image / tesseract img lstmbox                                      # make .lstmf training files
lstmtraining --continue_from eng.lstm --model_output out/myfont \
    --traineddata eng.traineddata --train_listfile list.train --max_iterations 3000
lstmtraining --stop_training --continue_from out/myfont_checkpoint \
    --traineddata eng.traineddata --model_output myfont.traineddata     # finalize
lstmeval --model myfont.traineddata --eval_listfile list.eval           # CER on held-out lines
```

Ground truth tips: one text line per image, tight crop with a few pixels of margin, same preprocessing you
will use in production, exact transcription including punctuation. Generate synthetic lines with
`text2image --font "My Font" --text corpus.txt` when you own the font, then mix in real scans.
Full training guide: [10-training-finetuning.md](10-training-finetuning.md).

---

## Known limits you cannot configure away

- No GPU. Ever. Parallelize across processes instead (`--jobs`, multiprocessing, tesserocr per worker).
- Reading order on multi-column and mixed layouts is heuristic. For Markdown-quality output use a document parser.
- Handwriting: not the tool. Curved or perspective text: not the tool.
- Tables come back as text lines; structure is gone. Use `img2table` on top or PP-StructureV3.
- Rotated text within a page (a sideways caption) is missed unless PSM 11/12 and even then often garbled.
- Confidence values are informative but not calibrated probabilities.

When any of these bite, the next stop is [02](02-engine-atlas.md) section B (RapidOCR, PaddleOCR) or C (Marker, Docling).
