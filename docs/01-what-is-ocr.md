# 01. What OCR actually is (and what it became)

[Back to README](../README.md) | Next: [Engine atlas](02-engine-atlas.md)

---

## The one-paragraph version

Optical Character Recognition takes an image and returns text. For thirty years that meant a single
program (Tesseract, ABBYY, OmniPage) that binarized the page, found lines, cut them into characters,
and classified each one. Since 2018 it means a **pipeline** of neural networks, and since 2024 it
increasingly means a **vision-language model** that looks at the whole page and writes Markdown.
The old engines did not go away. They are still the fastest and most predictable thing you can run on a
CPU. The new ones read handwriting, tables, formulas, and eleven-column newspaper scans. You need to
know both, and you need to know which layer of the stack each tool lives in.

---

## Vocabulary you will see everywhere

| Term | Meaning |
|:-----|:--------|
| **OCR** | Optical Character Recognition. Printed or rendered text to strings. |
| **HTR / ATR** | Handwritten Text Recognition / Automatic Text Recognition. The humanities world says ATR to cover both print and hand. |
| **STR** | Scene Text Recognition. Text in photos: signs, license plates, product labels. Different models, different benchmarks (ICDAR). |
| **DLA** | Document Layout Analysis. Finding regions: title, paragraph, table, figure, header, footer, footnote. |
| **Reading order** | The sequence in which regions should be read. Two-column papers break naive top-to-bottom. |
| **KIE** | Key Information Extraction. Turning an invoice into `{vendor, date, total}`. Downstream of OCR. |
| **Document parsing** | OCR + DLA + reading order + tables + formulas, emitted as Markdown/JSON/HTML. The 2026 meaning of "OCR a PDF". |
| **VLM** | Vision-Language Model. An image encoder bolted to an LLM decoder. Reads pages end to end. |
| **CER / WER** | Character / Word Error Rate. The metrics. Lower is better. See [09-evaluation](09-evaluation.md). |
| **Text-native PDF** | A PDF that already contains a text layer. Extract it with PyMuPDF; do not OCR it. |
| **Image PDF / scanned PDF** | A PDF that is only pictures of pages. This is what OCR is for. |
| **Searchable PDF / PDF-A** | A scanned PDF with an invisible OCR text layer added on top. OCRmyPDF's output. |
| **hOCR / ALTO / PAGE-XML** | XML formats that carry text plus bounding boxes plus confidences. Archives use ALTO and PAGE; the web world uses hOCR. |
| **traineddata** | A Tesseract model file (`eng.traineddata`). |
| **PSM / OEM** | Tesseract's Page Segmentation Mode and OCR Engine Mode. See [03](03-tesseract-deep-dive.md). |

Full glossary: [12-glossary.md](12-glossary.md).

---

## The pipeline (every engine does some subset of this)

```
  acquisition -> preprocessing -> layout analysis -> text detection -> recognition -> post-processing -> output
  (scan/photo)   (deskew,         (regions,          (word/line       (pixels to     (dictionary,        (txt, hOCR,
                  binarize,        reading order)     boxes)           characters)    LM, LLM,            ALTO, MD,
                  denoise)                                                            spell)              JSON, PDF-A)
```

| Stage | Classical (Tesseract) | DL pipeline (PaddleOCR) | VLM (PaddleOCR-VL, olmOCR) |
|:------|:----------------------|:------------------------|:---------------------------|
| Preprocessing | Mandatory. Otsu/Sauvola binarization inside Leptonica. Skew kills it. | Optional. Models trained on color photos. Mild deskew helps. | Do not binarize. Feed the color image at native resolution. |
| Layout | Heuristic column/block finding (PSM 3). Weak on multi-column. | Separate layout model (PP-DocLayoutV3, LayoutLMv3, YOLO variants). | Implicit, learned. Emits Markdown in reading order. |
| Detection | Connected components on the binary image. | DBNet / DBNet++ / CRAFT / FAST produce text-region masks. | Implicit. Some models can also emit boxes on request. |
| Recognition | LSTM + CTC over a text line. | CRNN, SVTR, PARSeq, ABINet over a cropped line. | Autoregressive LLM decoder over visual tokens. |
| Post-processing | Word dictionaries (DAWG), bigram LM, whitelist. | Optional. Usually none. | Built in (the LLM is the language model). |
| Output | txt, hOCR, TSV, ALTO, PDF. | Boxes + strings + confidences as JSON. | Markdown, HTML, JSON, DocTags. |

---

## Five generations of engines

### Generation 1: template and feature classifiers (1990s to 2016)

Tesseract 3's "legacy" engine, GOCR, Ocrad, CuneiForm. Segment characters, extract features, classify.
Works on typewritten English. Falls apart on ligatures, proportional fonts, anything touching. Still
selectable in Tesseract with `--oem 0` if you install the combined `tessdata` models. You will not use this
except to OCR a fixed-width receipt font that the LSTM model gets wrong.

### Generation 2: LSTM + CTC line recognizers (2016 to now)

Tesseract 4/5, OCRopus, Kraken, Calamari, PyLaia. A bidirectional LSTM slides over a normalized text
line and emits a character probability per column. **CTC** (Connectionist Temporal Classification) collapses
repeats and blanks so the model never needs character segmentation. This is why Tesseract 4 was a ten-point
accuracy jump over 3. These engines are small (a language model is 4 to 15 MB), run on CPU, are trainable
on a laptop, and are deterministic. Weaknesses: they need a clean horizontal line, so they inherit every
error of the layout/segmentation step above them.

### Generation 3: deep detector + recognizer pipelines (2019 to now)

PaddleOCR, EasyOCR, docTR, MMOCR, RapidOCR, OpenOCR. A **detection** CNN (DBNet, CRAFT, FAST) predicts a
text-probability heatmap for the whole image, polygons are extracted, each polygon is rectified and cropped,
and a **recognition** network (CRNN, SVTR, PARSeq) reads it. Because detection is learned, these handle
photos, rotation, curved text, and mixed fonts that Tesseract cannot. PP-OCRv5 and v6 are the mature
endpoint: a few megabytes per model, mobile and server tiers, 100+ languages, ONNX exportable.

### Generation 4: end-to-end transformers (2021 to 2024)

TrOCR (Microsoft), Donut, Nougat (Meta), GOT-OCR 2.0, Florence-2. A ViT encoder and a text decoder trained
together. TrOCR is still the best drop-in for **line-level handwriting**. Nougat showed you could go
straight from a page image to Markdown with LaTeX, and hallucinated enough to make everyone nervous.
These are the bridge to generation 5.

### Generation 5: VLM document parsers (2024 to now)

olmOCR (Allen AI), PaddleOCR-VL (Baidu), DeepSeek-OCR and DeepSeek-OCR-2, GLM-OCR (Z.ai), dots.ocr,
HunyuanOCR (Tencent), Chandra and Surya 2 (Datalab), Nanonets-OCR2, LightOnOCR, Granite-Docling (IBM),
MinerU 2.5, MonkeyOCR, plus general VLMs like Qwen3-VL and MiniCPM-V. A vision encoder compresses the page
into a few hundred to a few thousand tokens and an LLM decoder writes structured output: Markdown with
tables, LaTeX, reading order, sometimes bounding boxes. The 2026 state of the art on OmniDocBench is
in this class, and the leading models are **under 1 billion parameters** (PaddleOCR-VL 0.9B, GLM-OCR,
LightOnOCR 1B), which means an 8 GB consumer GPU runs them. Weaknesses: they can invent text that is not
there, they are slower than generation 2 on CPU by two orders of magnitude, and their confidence scores
are not calibrated the way Tesseract's are.

---

## Concepts that decide whether your OCR works

### Resolution

Recognition networks were trained on text of a certain pixel height. For Tesseract the rule is
**x-height at least 20 pixels**, which for 10 to 12 point body text means **300 DPI**. At 150 DPI a lower-case
letter is about 10 px tall and accuracy collapses. Screenshots at 96 DPI are the classic failure:
upscale them 2x to 3x with Lanczos before Tesseract. DL detectors have a similar floor (they usually
resize the long side to 960 or 1280 px internally, so a 4000 px photo of a page is fine but a 400 px
thumbnail is not). VLMs tile or resize the page to their encoder's native grid; a 1024 to 1600 px long side
is the usual sweet spot.

### Binarization

Turning gray into pure black and white. Global Otsu picks one threshold for the page and fails on uneven
lighting; Sauvola and adaptive Gaussian compute a local threshold per window and survive shadows.
Tesseract binarizes internally with Otsu (Leptonica) unless you set `thresholding_method`. Doing your own
Sauvola pass first is the single most effective preprocessing step for phone photos of paper.
See [08-preprocessing](08-preprocessing.md).

### Skew and orientation

Generation 2 engines assume lines are horizontal. Two degrees of skew is enough to merge lines. Tesseract's
`osd` model detects 0/90/180/270 rotation and script; it does not deskew small angles. Deskew with
OpenCV (`minAreaRect` on the text mask or a Hough-line vote) or `unpaper`, or let `ocrmypdf --deskew` do it.

### Dictionaries and language models

Tesseract loads word lists (`*.dawg`) and a character bigram model and uses them to break ties. This is
why it turns `c0de` into `code`. Turn dictionaries off (`load_system_dawg=0 load_freq_dawg=0`) when you
OCR serial numbers, hashes, or code. VLMs have the opposite problem: their LLM decoder is a very strong
language model and will silently "fix" a misspelled word in the original into the correct spelling.

### Confidence

Tesseract returns per-word confidence 0 to 100 (`tesseract img out tsv`). PaddleOCR returns a per-line
score 0 to 1. VLMs return token log-probabilities that are not comparable across models and usually not
exposed by the wrapper. If you need a "review queue", generation 2 and 3 give you a usable signal;
generation 5 mostly does not.

### Hallucination

A VLM that cannot read a smudged word will write the most probable word. A classical engine will write
garbage. Garbage is detectable; a plausible wrong word is not. For legal, medical, financial, and archival
work this is the argument for running a classical engine alongside the VLM and diffing.

---

## Where each class fails

| Input | Tesseract 5 | PaddleOCR / RapidOCR | VLM parser | What to do |
|:------|:------------|:---------------------|:-----------|:-----------|
| Clean 300 DPI office scan | Excellent | Excellent | Excellent, slower | Tesseract via OCRmyPDF |
| Phone photo of a page, shadows | Poor | Good | Very good | Sauvola + RapidOCR, or VLM |
| Two-column academic PDF | Wrong reading order | Boxes fine, order manual | Excellent | Marker / MinerU / Docling |
| Tables | Text only, no structure | PP-StructureV3 rebuilds cells | Markdown/HTML tables | PP-StructureV3 or Docling |
| Math | Garbage | Garbage unless formula model | LaTeX | pix2tex on crops, or MinerU/Marker |
| Handwriting | Near zero | Weak | Good (Surya 2, Qwen3-VL) | VLM or TrOCR |
| 1700s print, long-s, blackletter | Needs `frk`/custom model | Weak | Surprisingly decent | Kraken with a trained model |
| Screenshot, 11 px UI font | Poor unless upscaled | Fine | Fine | OneOCR / Windows OCR, or upscale 3x |
| Serial numbers, hex, code | Dictionary corruption | Fine | LLM "corrects" it | Tesseract with dawgs off + whitelist |
| 10,000 pages on a laptop CPU | Hours, fine | Hours, fine | Days | OCRmyPDF `--jobs`, RapidOCR pool |
| Right-to-left scripts | Good with `ara`/`heb` | Good | Model dependent | OCRmyPDF 17 fixed RTL extraction |
| Vertical CJK | `jpn_vert`, `chi_tra_vert` | PaddleOCR handles | Model dependent | PaddleOCR or YomiToku |

---

## Formats you will output

| Format | Carries | Produced by | Consumed by |
|:-------|:--------|:------------|:------------|
| Plain text | text | everything | grep, LLMs |
| TSV | text + word boxes + confidence | Tesseract | review tooling, pandas |
| hOCR | HTML with boxes, lines, paragraphs, confidence | Tesseract, OCRmyPDF, Kraken | hocr-tools, PDF renderers |
| ALTO XML | archival layout + text + coordinates | Tesseract, Kraken, OCR-D, ABBYY | libraries, METS/ALTO viewers |
| PAGE XML | richer layout ground truth | eScriptorium, Kraken, OCR-D, Transkribus | training pipelines |
| Searchable PDF / PDF-A | original image + invisible text | OCRmyPDF, Tesseract `pdf` | every PDF viewer, Paperless |
| Markdown | reading-order text + tables + LaTeX | Marker, MinerU, Docling, olmOCR, VLMs | RAG, LLM prompts |
| JSON (boxes + strings) | per-line polygons, text, score | PaddleOCR, RapidOCR, EasyOCR, docTR, Surya | your code |
| DocTags | IBM's compact layout markup | Granite-Docling | Docling converts to MD/JSON |

---

## How to read the rest of this repo

- You already run Tesseract. Read [03](03-tesseract-deep-dive.md) to make sure you run it right (most people run it wrong: 96 DPI screenshots, `tessdata_fast`, default PSM on a receipt).
- Then read [02](02-engine-atlas.md) once, top to bottom, so the names stop being noise.
- Then jump to the recipe in [06](06-pairing-recipes.md) that matches your document type and run it.
- Then run `scripts/ocr_bench.py` on ten of your own pages with a ground truth you typed. That number decides everything else.
