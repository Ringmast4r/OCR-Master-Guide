# 06. Pairing recipes

[Back to README](../README.md) | Prev: [Linux stack](05-linux-stack.md) | Next: [VLM document parsers](07-vlm-document-parsers.md)

Fourteen end-to-end pipelines. Each one names the input, the engines, the glue, and the trap. The
philosophy behind them: **preprocess for classical engines, not VLMs; detection and recognition are
separable; text-native PDFs skip OCR; two engines plus a diff beat one; LLM correction is measured, not
assumed.**

Every recipe assumes the venv from [04](04-windows-stack.md) or [05](05-linux-stack.md) is active.

---

## Recipe 1. Screenshots and UI text

**Input:** anti-aliased text at 96 DPI, error dialogs, terminal windows, chat logs, video frames.
**Trap:** Tesseract at native size returns nothing or garbage because x-height is 8 to 12 px.

| OS | Interactive | Scripted |
|:---|:------------|:---------|
| Windows | PowerToys Text Extractor (Win+Shift+T), Snipping Tool text actions | `oneocr` or `winocr` ([scripts/windows_native_ocr.py](../scripts/windows_native_ocr.py)) |
| Linux | NormCap, Frog | `maim -s \| tesseract stdin stdout --psm 6` after 3x upscale |
| Any | NormCap | RapidOCR (handles small text without upscaling) |

```python
# Tesseract fallback that actually works on screenshots
import cv2, pytesseract
g = cv2.cvtColor(cv2.imread("shot.png"), cv2.COLOR_BGR2GRAY)
g = cv2.resize(g, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
print(pytesseract.image_to_string(g, config="--psm 6 -c user_defined_dpi=300"))
```

Dark-mode screenshots: invert first (`255 - g`) or let `tessedit_do_invert=1` (default) handle it; RapidOCR and OneOCR do not care.

---

## Recipe 2. Clean scanned PDFs to searchable PDFs (the archive job)

**Input:** office scans, 200 to 300 DPI, mostly text, one language.
**Engine:** Tesseract via OCRmyPDF. Nothing else is worth the complexity here.

```bash
ocrmypdf --deskew --rotate-pages --clean --clean-final --skip-text --optimize 3 \
    --output-type pdfa -l eng --jobs 8 --sidecar out.txt in.pdf out.pdf
```

Windows (no unpaper): drop `--clean --clean-final`. Better accuracy: install `tessdata_best` `eng` and
add `--tesseract-oem 1`. Mixed languages: `-l eng+deu+fra`. Bad existing OCR: `--redo-ocr`.
Bulk: GNU parallel or the PowerShell loop in [04](04-windows-stack.md).
Storage: Paperless-ngx runs exactly this on a watched folder and indexes the result.

---

## Recipe 3. Phone photos and messy scans

**Input:** shadows, curl, perspective, uneven paper, JPEG artifacts.
**Engine:** RapidOCR (CPU) or PaddleOCR (GPU) after OpenCV cleanup. Tesseract only after heavy preprocessing.

```python
# preprocess with the repo script, then RapidOCR
# python scripts/preprocess.py photo.jpg --perspective --deskew --binarize sauvola --denoise -o clean.png
from rapidocr import RapidOCR
engine = RapidOCR()
res = engine("photo.jpg")                # RapidOCR wants the ORIGINAL color image, not the binarized one
print(res.txts, res.scores)
res.vis("boxes.png")
```

PaddleOCR 3.x with its own unwarping and orientation modules (GPU or patient CPU):

```python
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_doc_orientation_classify=True, use_doc_unwarping=True, use_textline_orientation=True, lang="en")
for r in ocr.predict("photo.jpg"):
    r.print(); r.save_to_img("out/"); r.save_to_json("out/")
```

**Pairing rule:** Sauvola-binarize for Tesseract; give RapidOCR/PaddleOCR the color photo, at most deskewed
and perspective-corrected. If you must use Tesseract on a photo, run `preprocess.py` first and expect 90 percent, not 99.

---

## Recipe 4. PDFs with layout to Markdown (LLM ingestion, RAG)

**Input:** reports, papers, manuals, two columns, tables, figures, footnotes, math.
**Engine:** Marker (GPU), Docling (CPU-friendly, MIT), or MinerU (academic, AGPL). All three first check for a
text layer and only OCR image pages.

```bash
# Marker
pip install marker-pdf
marker_single report.pdf --output_dir out --output_format markdown       # add --use_llm --gemini_api_key ... or --llm_service marker.services.ollama.OllamaService for table/form upgrades
marker ./pdfs --workers 4                                                 # folder

# Docling, with RapidOCR instead of the default EasyOCR
pip install docling rapidocr
docling report.pdf --ocr-engine rapidocr --to md --output out/
# Docling with the Granite-Docling VLM (CPU works, GPU faster)
docling report.pdf --pipeline vlm --vlm-model granite_docling --to md

# MinerU
pip install "mineru[core]"
mineru -p report.pdf -o out/ -b pipeline        # or -b vlm-transformers, -b vlm-vllm-engine (Linux)
```

Python (Docling):

```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
opts = PdfPipelineOptions(do_ocr=True, do_table_structure=True, ocr_options=RapidOcrOptions())
conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
doc = conv.convert("report.pdf").document
open("report.md", "w", encoding="utf-8").write(doc.export_to_markdown())
```

**Trap:** all three emit Markdown that *looks* right. Spot-check tables and footnotes against the PDF.
For measured quality, run OmniDocBench on a sample ([09](09-evaluation.md)).

---

## Recipe 5. Best-possible accuracy with a GPU (VLM parser)

**Input:** anything from recipe 4 where Marker/Docling made mistakes you cannot accept.
**Engine:** PaddleOCR-VL 1.6 (0.9B), DeepSeek-OCR-2, dots.ocr, or Chandra (needs 16 GB or the quantized build).

```python
# PaddleOCR-VL through PaddleOCR itself (Windows and Linux, GPU)
from paddleocr import PaddleOCRVL
pipe = PaddleOCRVL()
for r in pipe.predict("page.png"):
    r.save_to_markdown("out/"); r.save_to_json("out/")
```

```bash
# vLLM server route (Linux / WSL2), then post pages from any client
vllm serve deepseek-ai/DeepSeek-OCR-2 --trust-remote-code --port 8000 --gpu-memory-utilization 0.9
```

```python
import base64, openai
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="x")
img = base64.b64encode(open("page.png", "rb").read()).decode()
r = client.chat.completions.create(model="deepseek-ai/DeepSeek-OCR-2", messages=[{"role": "user", "content": [
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}},
    {"type": "text", "text": "<|grounding|>Convert the document to markdown."}]}])
print(r.choices[0].message.content)
```

Prompts are model-specific (DeepSeek uses `<|grounding|>` and `<image>\nFree OCR.`; PaddleOCR-VL has task
tokens; olmOCR builds its own prompt with page metadata). Read the model card. Model routes and VRAM fit:
[07](07-vlm-document-parsers.md).

**Pairing rule:** VLM output for Markdown, plus a RapidOCR pass on the same page for a word-level diff
(recipe 13) if the content is legal, financial, or medical.

---

## Recipe 6. Receipts, invoices, forms (key information extraction)

**Input:** semi-structured documents where you want fields, not prose.

| Route | Stack | When |
|:------|:------|:-----|
| Local, open | PaddleOCR PP-StructureV3 (layout + tables) -> JSON -> local LLM (Qwen3 via Ollama) for field mapping | Privacy, volume |
| Local, one model | Nanonets-OCR2-3B or PaddleOCR-VL -> Markdown with tables -> LLM | GPU available |
| Cloud | Azure Document Intelligence prebuilt-invoice / prebuilt-receipt | Accuracy on standard forms, $10 per 1,000 pages |
| Legacy DL | Donut, LayoutLMv3 fine-tuned on CORD/SROIE/FUNSD | You have labeled training data |

```python
# PP-StructureV3 to Markdown, then ask a local LLM for JSON
from paddleocr import PPStructureV3
pipe = PPStructureV3()
out = pipe.predict("invoice.png")
for r in out: r.save_to_markdown("out/")
md = open("out/invoice.md", encoding="utf-8").read()

import ollama, json
r = ollama.chat(model="qwen3:8b", messages=[{"role": "user", "content":
    "Extract vendor, invoice_number, date, currency, line_items[{description, qty, unit_price, total}], subtotal, tax, total "
    "as JSON from this OCR markdown. Use null for missing fields. Do not invent values.\n\n" + md}], format="json")
print(json.loads(r["message"]["content"]))
```

Tesseract-only receipts: `--psm 4` (single column, variable size), `preserve_interword_spaces=1`, dictionaries off
for the numeric columns, `tessedit_char_whitelist=0123456789.,$-` on a cropped price column.

---

## Recipe 7. Handwriting

**Modern (notes, forms, letters):**

```bash
# Surya 2 (GPU): full page, layout aware
surya_ocr notes.jpg --output_dir out
# Qwen3-VL via Ollama: robust, slower, free-form
ollama run qwen3-vl:8b "Transcribe this handwritten page exactly. Keep line breaks. Mark unreadable words as [?]. ./notes.jpg"
```

Line-level with TrOCR after your own segmentation (or PaddleOCR's detector):

```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
proc = TrOCRProcessor.from_pretrained("microsoft/trocr-large-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-large-handwritten").to("cuda")
for crop in line_crops:                      # PIL images of single lines, from RapidOCR/Paddle detection boxes
    px = proc(images=crop, return_tensors="pt").pixel_values.to("cuda")
    print(proc.batch_decode(model.generate(px, max_new_tokens=64), skip_special_tokens=True)[0])
```

**Historical (letters, registers, manuscripts):** Kraken + eScriptorium, or Transkribus. Transcribe 50 to 200 lines,
train, run, correct, retrain. [10](10-training-finetuning.md). Public models: Zenodo `ocr_models` community,
Transkribus public models, HTR-United datasets.

**Trap:** VLMs normalize spelling and expand abbreviations. For diplomatic transcription (what is written, not
what was meant) use Kraken/PyLaia trained on your material.

---

## Recipe 8. Math

| Input | Tool |
|:------|:-----|
| A single formula crop | `pix2tex` (CLI, GUI, or `from pix2tex.cli import LatexOCR`), `texify`, UniMERNet |
| Whole pages with math | Marker, MinerU (`-b pipeline` uses UniMERNet-class models; `-b vlm` uses MinerU2.5), Nougat, Nanonets-OCR2, PaddleOCR-VL |
| Handwritten math | UniMERNet, Qwen3-VL, Mathpix (commercial) |

```bash
pip install "pix2tex[gui]"
latexocr                     # GUI with screenshot button
pix2tex formula.png          # CLI
```

Pairing: MinerU or Marker for the page (they call a formula model on detected formula regions), pix2tex to
re-do the formulas the page model garbled. Validate LaTeX by compiling it or rendering with KaTeX.

---

## Recipe 9. Tables

| Route | Stack | Output |
|:------|:------|:-------|
| Lines-visible tables, CPU | `img2table` + Tesseract/RapidOCR | pandas, xlsx |
| Any table, GPU | PP-StructureV3 (wired + wireless table models) | HTML, Markdown, xlsx |
| Table crop | Surya `surya_table`, Table Transformer | cells + rows/cols |
| Inside a document parser | Docling (`do_table_structure=True`, TableFormer), Marker (`--use_llm` improves merged cells) | Markdown/HTML |
| VLM | PaddleOCR-VL, Nanonets-OCR2, DeepSeek-OCR-2 | Markdown/HTML tables |

```python
from img2table.document import Image
from img2table.ocr import TesseractOCR
tbl = Image("table.png").extract_tables(ocr=TesseractOCR(lang="eng"), implicit_rows=True, borderless_tables=True)
for t in tbl: print(t.df)
```

Evaluate with TEDS (tree edit distance similarity) if it matters ([09](09-evaluation.md)).

---

## Recipe 10. CJK, Arabic, Indic, mixed scripts

| Script | First choice | Second |
|:-------|:-------------|:-------|
| Simplified/Traditional Chinese | PaddleOCR (`lang="ch"`, PP-OCRv5 is trained on it), RapidOCR | Tesseract `chi_sim`/`chi_tra` (+`_vert`), DeepSeek-OCR, GLM-OCR |
| Japanese | YomiToku (documents), manga-ocr (manga), PaddleOCR `japan` | Tesseract `jpn`/`jpn_vert` |
| Korean | PaddleOCR `korean` | Tesseract `kor` |
| Arabic, Persian, Urdu | Kraken (trained models on Zenodo), PaddleOCR `ar` | Tesseract `ara`/`fas`/`urd` with OCRmyPDF 17 for RTL PDFs |
| Hebrew | Tesseract `heb`, Kraken | dots.ocr |
| Devanagari, Bengali, Tamil, etc. | Tesseract `script/Devanagari` etc. (best of the open engines for Indic), PaddleOCR `devanagari` | Surya (90+ languages), dots.ocr |
| Cyrillic | Tesseract `rus`/`script/Cyrillic`, PaddleOCR `cyrillic` | Surya |
| Mixed unknown | Tesseract `--psm 0 -l osd` to detect script, then route | dots.ocr (100 languages in one model) |

Tesseract multi-language: `-l eng+chi_sim` costs speed; prefer the script model or route per region.

---

## Recipe 11. Bulk: thousands of pages

**CPU only:** OCRmyPDF `--jobs $(nproc)` per file plus GNU parallel across files, or a RapidOCR worker pool:

```python
from concurrent.futures import ProcessPoolExecutor
from rapidocr import RapidOCR
_eng = None
def work(path):
    global _eng
    _eng = _eng or RapidOCR()
    r = _eng(path)
    return path, "\n".join(r.txts or [])
with ProcessPoolExecutor(max_workers=8) as ex:
    for path, txt in ex.map(work, image_paths, chunksize=16):
        open(path + ".txt", "w", encoding="utf-8").write(txt)
```

**GPU:** vLLM server with PaddleOCR-VL or DeepSeek-OCR-2, many concurrent requests (vLLM batches them), or the
olmOCR pipeline (`python -m olmocr.pipeline ./workspace --pdfs ...`), which manages queues, retries, and
resumption for you. Rasterize at 1024 to 1536 px long side, not 300 DPI; VLMs do not need more.

**Both:** check the text layer first and skip born-digital pages:

```python
import fitz
doc = fitz.open("in.pdf")
needs_ocr = [i for i, p in enumerate(doc) if len(p.get_text("text").strip()) < 20]
```

---

## Recipe 12. LLM post-correction (with a measurement harness)

**Claim:** an LLM fixes OCR errors. **Reality (ICDAR 2026 HIPE-OCRepair, "No Free Lunches" 2025):** it fixes
obvious ones and introduces plausible new ones; net gain depends on the text and the prompt, and can be negative.
So: always measure CER on a held-out sample before and after.

```python
import ollama, jiwer
raw = open("ocr_raw.txt", encoding="utf-8").read()
gt  = open("ground_truth.txt", encoding="utf-8").read()
prompt = ("You are correcting OCR output. Fix only clear OCR errors (split/merged words, l/1/I, rn/m, 0/O, "
          "stray punctuation). Do NOT change spelling that could be original, do NOT modernize, do NOT add or remove "
          "content, do NOT translate. Return only the corrected text.\n\n" + raw)
fixed = ollama.chat(model="qwen3:8b", messages=[{"role": "user", "content": prompt}])["message"]["content"]
print("CER before", jiwer.cer(gt, raw), "after", jiwer.cer(gt, fixed))
```

Constrain the model: short chunks (one paragraph), low temperature, an explicit "do not" list, and a diff check
that rejects edits changing more than N percent of characters. For names, numbers, and codes, forbid edits entirely
(mask them before the LLM, restore after).

---

## Recipe 13. Ensemble: two engines and a diff

Run Tesseract and RapidOCR (or any two dissimilar engines), align at word level, and flag disagreements.
Where both agree you have high confidence without any calibrated score; where they disagree a human or a
third engine decides.

```python
import difflib, pytesseract, cv2
from rapidocr import RapidOCR
img = cv2.imread("page.png")
a = pytesseract.image_to_string(img, config="--psm 6").split()
b = " ".join(RapidOCR()(img).txts or []).split()
sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != "equal":
        print(tag, "tesseract:", " ".join(a[i1:i2]), "| rapidocr:", " ".join(b[j1:j2]))
```

Three engines and majority vote (a poor man's ROVER) is the classic trick in archival OCR; Calamari has it built in
(`--voter`). Diffs are also the cheapest hallucination detector for VLM output.

---

## Recipe 14. Video and live camera

Sample frames (every N frames or on scene change), dedupe with perceptual hash, run RapidOCR/PaddleOCR (they
handle rotation and scene text), merge consecutive identical results.

```python
import cv2, imagehash
from PIL import Image
from rapidocr import RapidOCR
eng, seen = RapidOCR(), set()
cap = cv2.VideoCapture("clip.mp4"); n = 0
while True:
    ok, frame = cap.read()
    if not ok: break
    if n % 15 == 0:
        h = str(imagehash.phash(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))))
        if h not in seen:
            seen.add(h)
            r = eng(frame)
            if r.txts: print(n, r.txts)
    n += 1
```

Mobile: ML Kit (Android/iOS) or Apple Vision on-device. Subtitles/hardsubs: VideoSubFinder + Tesseract, or
PaddleOCR on the bottom crop.

---

## Which recipe when (index)

| Situation | Recipe |
|:----------|:------:|
| Error message on screen | 1 |
| Scanner output to archive | 2 |
| Photo of a document | 3 |
| Feed PDFs to an LLM | 4 |
| Need the best, have a GPU | 5 |
| Invoices, receipts, forms | 6 |
| Handwriting | 7 |
| Formulas | 8 |
| Tables | 9 |
| Non-Latin scripts | 10 |
| Thousands of pages | 11 |
| OCR output is nearly right | 12 |
| Must not miss errors | 13 |
| Video | 14 |
