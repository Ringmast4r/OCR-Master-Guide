# 09. Evaluation

[Back to README](../README.md) | Prev: [Preprocessing](08-preprocessing.md) | Next: [Training and fine-tuning](10-training-finetuning.md)

You cannot choose between engines without a number, and the number that matters is the one on *your*
documents. This guide covers the metrics, the tools that compute them, the public benchmarks people quote,
and how to build a ground-truth set in an afternoon.

---

## Metrics

| Metric | Definition | Use for | Notes |
|:-------|:-----------|:--------|:------|
| **CER** (character error rate) | `(S + D + I) / N` over characters, Levenshtein alignment | Everything | Can exceed 1.0 with many insertions. 0.02 = 98 percent character accuracy |
| **WER** (word error rate) | Same over whitespace-split tokens | Readability, search | One wrong character = one wrong word; harsher than CER |
| **Character accuracy** | `1 - CER` (clipped) | Slide decks | Same information |
| **Bag-of-words F1** | Precision/recall on the multiset of words, order ignored | Reading-order-insensitive comparison | Useful when layout engines reorder paragraphs |
| **cMER** (character match error rate) | Match-based variant used by HIPE-OCRepair 2026 | Post-correction competitions | Penalizes hallucinated additions more clearly |
| **TEDS** | Tree edit distance similarity on HTML tables | Table structure | 0 to 1, higher better; TEDS-S ignores cell text |
| **Edit distance on LaTeX / CDM** | Normalized edit distance or character detection metric on formulas | Math | UniMERNet and OmniDocBench use CDM |
| **Reading-order edit distance** | Edit distance over block sequence | Layout | OmniDocBench reports it |
| **Detection F1 / IoU** | Box overlap with ground-truth boxes | Text detection models | ICDAR-style |
| **Confidence calibration** | Does conf 0.9 mean 90 percent right | Review queues | Tesseract: roughly; VLMs: no |

Normalization before scoring matters more than people admit: Unicode NFC, whitespace collapse, quote/dash
folding, case. Decide once, apply to both sides, write it down. Historical text needs special handling of
long-s, ligatures, and hyphenation (dinglehopper and ocrevalUAtion have built-in rules).

---

## Tools

| Tool | What | Install |
|:-----|:-----|:--------|
| [jiwer](https://github.com/jitsi/jiwer) | CER/WER/MER/WIL with composable normalization transforms | `pip install jiwer` |
| [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) | Fast Levenshtein, alignment ops, in C++ | `pip install rapidfuzz` |
| [dinglehopper](https://github.com/qurator-spk/dinglehopper) | OCR-D's evaluator: CER/WER + HTML diff report, reads PAGE/ALTO/text | `pip install dinglehopper` |
| [ocrevalUAtion](https://github.com/impactcentre/ocrevalUAtion) | IMPACT Centre's Java tool, classic in digitization projects | jar |
| [ISRI ocreval](https://github.com/eddieantonio/ocreval) | The 1990s UNLV/ISRI accuracy tools, still used in papers (`accuracy`, `wordacc`) | build from source |
| [hocr-tools](https://github.com/ocropus/hocr-tools) | `hocr-eval`, `hocr-eval-lines` for hOCR vs ground truth | `pip install hocr-tools` |
| [TEDS](https://github.com/ibm-aur-nlp/PubTabNet/tree/master/src) | Reference implementation from PubTabNet | repo |
| [OmniDocBench](https://github.com/opendatalab/OmniDocBench) | Full end-to-end document parsing evaluation with its dataset | repo |
| [olmOCR-Bench](https://github.com/allenai/olmocr/tree/main/olmocr/bench) | Unit-test style checks over ~1,400 PDFs | `pip install olmocr[bench]` |
| [`scripts/ocr_bench.py`](../scripts/ocr_bench.py) | This repo: every installed engine on one image, timing + CER | included |

```python
import jiwer
tf = jiwer.Compose([jiwer.ToLowerCase(), jiwer.RemoveMultipleSpaces(), jiwer.Strip(), jiwer.RemovePunctuation()])
gt  = open("gt.txt", encoding="utf-8").read()
hyp = open("hyp.txt", encoding="utf-8").read()
print("CER", jiwer.cer(gt, hyp, truth_transform=tf, hypothesis_transform=tf))
print("WER", jiwer.wer(gt, hyp, truth_transform=tf, hypothesis_transform=tf))
out = jiwer.process_words(gt, hyp)
print(jiwer.visualize_alignment(out))          # see exactly which words broke
```

```bash
dinglehopper gt.txt ocr.txt report          # report.html shows a colored character diff
```

---

## Public benchmarks (what the leaderboards measure)

| Benchmark | Domain | What it scores | Who quotes it |
|:----------|:-------|:---------------|:--------------|
| **OmniDocBench v1.7** (Apr 2026) | 1,000+ diverse PDF pages, EN + ZH; text, tables, formulas, reading order | Overall + per-element edit distances, TEDS, CDM | PaddleOCR-VL, DeepSeek-OCR, GLM-OCR, MinerU, dots.ocr, HunyuanOCR |
| **olmOCR-Bench** | 1,400+ real PDFs, 7,000 unit tests (text present/absent, order, table cells, math) | Pass rate, overall score | olmOCR, Chandra, Marker, MinerU, Nanonets, Docling |
| **OCRBench / OCRBench v2** | VLM text reading + reasoning | Score | General VLMs (Qwen3-VL, MiniCPM-V) |
| **DocVQA** | Question answering over document images | ANLS | General VLMs |
| **FUNSD, CORD, SROIE** | Forms, receipts, invoices (KIE) | Field F1 | LayoutLM family, Donut, KIE papers |
| **PubTabNet, FinTabNet, PubTables-1M** | Tables | TEDS | Table Transformer, TableFormer |
| **IAM, RIMES, READ** | Handwriting lines | CER/WER | TrOCR, PyLaia, Kraken |
| **ICDAR RRC (2013/2015/2019 MLT, ArT)** | Scene text | Detection F1, recognition accuracy | PaddleOCR, MMOCR, PARSeq |
| **UniMER-Test** | Formulas (printed, handwritten, screenshot, noisy) | BLEU, edit distance, ExpRate | UniMERNet, pix2tex, Texify |
| **HIPE-OCRepair 2026** | LLM post-correction of historical OCR | cMER, preference score | Post-correction papers |

Published numbers as of the README snapshots used in this repo (both change monthly; follow the links in [13](13-link-index.md)):

**OmniDocBench v1.6_full, OpenDataLab, updated 30 Apr 2026, overall score:**
PaddleOCR-VL-1.6 96.3 (Baidu, 0.9B), MinerU2.5-Pro 95.8 (OpenDataLab, 1.2B), GLM-OCR 95.2 (Z.ai, 0.9B),
PaddleOCR-VL-1.5 94.9, PaddleOCR-VL 94.2, Youtu-Parsing 93.7 (Tencent, 2.5B), Qianfan-OCR 93.9 (Baidu, 4B),
Ovis2.6-30B-A3B 93.7, Logics-Parsing-v2 93.3 (Alibaba, 4B), ABot-OCR 93.3 (Amap, 2B), FireRed-OCR 93.3 (2B),
MinerU-2.5 93.0, Gemini 3 Pro 92.9, Gemini 3 Flash 92.6, dots.ocr 90.8 (RedNote, 3B).

**olmOCR-Bench, Ai2, README table (olmOCR v0.4.0 era):**
Chandra 0.1 83.1 (Datalab, 8B), Infinity-Parser 7B 82.5, olmOCR-2 v0.4.0 82.4 (Ai2, 7B), PaddleOCR-VL 80.0,
Marker 1.10.1 76.1, DeepSeek-OCR 75.7, MinerU 2.5.4 75.2, Mistral OCR API 72.0, Nanonets-OCR2-3B 69.5.

The two boards disagree on the winner because they measure different things: OmniDocBench is half Chinese and
weights tables and formulas heavily; olmOCR-Bench is English PDFs with old scans, tiny text, and multi-column
unit tests. PaddleOCR-VL is the only model in the top tier of both that fits an 8 GB GPU.

Classical engines are missing from the modern leaderboards because those measure Markdown structure. On
plain-text CER for printed English, docTR (0.197 on one messy invoice set) tied Surya 2 (0.191) in a 2026
comparison, and a tuned Tesseract on clean 300 DPI scans is routinely under 0.01. Different task, different scale.

---

## Build your own ground truth (the afternoon version)

1. **Pick 20 to 50 pages** that represent your real inputs: worst 25 percent, typical 50 percent, best 25 percent.
2. **Run the best engine you have** (a VLM or PaddleOCR) to get a draft transcription.
3. **Correct the draft by hand** in a text editor next to the image. It is 3 to 5 times faster than typing from scratch.
   Keep line breaks as on the page. Do not "fix" the original's typos.
4. **Save as UTF-8** `NNNN.gt.txt` next to `NNNN.png`. This is also the format tesstrain and Kraken want.
5. **Decide normalization** (case, punctuation, whitespace, hyphenation) and encode it as a jiwer transform.
6. **Run every candidate engine** with `scripts/ocr_bench.py --gt`, log CER and seconds per page in a CSV.
7. **Look at the worst 5 pages per engine.** Failure *modes* matter more than the mean: one engine that drops
   footnotes is worse for you than one that confuses l and 1 everywhere.

For tables and layout, ground truth is HTML or Markdown and the metric is TEDS or olmOCR-style unit tests
("the string `Total 1,234.56` appears", "row 3 col 2 equals X"). Write ten such asserts per page in a JSON file
and a 20-line script; it beats any generic score.

Labeling tools when you outgrow a text editor: [Label Studio](https://labelstud.io/) (boxes + transcription),
eScriptorium (lines + transcription, exports PAGE-XML), Transkribus, [OCR-D's browse-ocrd](https://github.com/hnesk/browse-ocrd).

---

## Reporting

A useful comparison table looks like this:

| Engine | Version | Preproc | CER | WER | s/page (CPU/GPU) | Worst failure mode |
|:-------|:--------|:--------|:---:|:---:|:----------------:|:-------------------|
| Tesseract | 5.5.3 best | sauvola+deskew | 0.031 | 0.092 | 1.1 CPU | Two-column order, footnotes merged |
| RapidOCR | 3.x v6 | none | 0.018 | 0.061 | 0.6 CPU | Drops superscripts |
| PaddleOCR-VL | 1.6 | none | 0.009 | 0.024 | 0.9 GPU | Normalized two spellings |

(Illustrative numbers, not measurements.) Keep the CSV under version control next to the ground truth; rerun
when you upgrade anything.
