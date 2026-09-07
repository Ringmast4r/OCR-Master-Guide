# 02. Engine atlas

[Back to README](../README.md) | Prev: [What OCR is](01-what-is-ocr.md) | Next: [Tesseract deep dive](03-tesseract-deep-dive.md)

Every engine, model, wrapper, desktop app, and cloud API worth knowing in September 2026, grouped by
what layer of the stack it lives in. Columns: **GPU** = needs or benefits from one. **Win/Linux** = runs
natively there (WSL2 counts as Linux). **Install** = the shortest line that works. Versions are the
latest I could confirm; click the link and check the releases page before you depend on a number.

Legend for GPU: `no` = CPU only, `opt` = CPU works and GPU is faster, `yes` = practically requires a GPU.

---

## A. Classical line OCR (generation 1 and 2)

| Engine | License | GPU | Win | Linux | Best for | Weak spot | Install |
|:-------|:--------|:----|:----|:------|:---------|:----------|:--------|
| [Tesseract 5.5.3](https://github.com/tesseract-ocr/tesseract) | Apache-2.0 | no | yes | yes | Clean printed scans, 100+ languages, searchable PDFs, deterministic CLI | Skew, noise, photos, handwriting, multi-column order | Win: `winget install UB-Mannheim.TesseractOCR`. Deb: `apt install tesseract-ocr` |
| [Kraken 5](https://github.com/mittagessen/kraken) | Apache-2.0 | opt | WSL | yes | Historical print, non-Latin (Arabic, Hebrew, Syriac), trainable, ALTO/PAGE out | Modern-doc layout, Windows native | `pip install kraken` (Linux/macOS) |
| [Calamari 2.x](https://github.com/Calamari-OCR/calamari) | Apache-2.0 | opt | yes | yes | Line OCR with model voting, OCR-D pipelines, historical print | Needs external segmentation | `pip install calamari-ocr` |
| [OCRopus / ocropy](https://github.com/ocropus-archive/DUP-ocropy) | Apache-2.0 | no | no | yes | The ancestor of Kraken and Calamari; read the code | Python 2 era, archived | historical interest only |
| [Ocrad](https://www.gnu.org/software/ocrad/) | GPL-3.0 | no | cygwin | yes | Tiny C++ feature-based OCR, embedded use | Accuracy | `apt install ocrad` |
| [GOCR](https://jocr.sourceforge.net/) | GPL-2.0 | no | yes | yes | Same class as Ocrad; barcode-ish inputs | Accuracy | `apt install gocr` |
| [CuneiForm](https://launchpad.net/cuneiform-linux) | BSD | no | yes | yes | Cyrillic-era ABBYY-derived engine | Abandoned since 2011 | `apt install cuneiform` |

**What to take away:** Tesseract is the only one you install by default. Kraken and Calamari are what you
reach for when you need to *train* a line recognizer on a specific typeface or manuscript.

---

## B. Deep-learning detector + recognizer pipelines (generation 3)

| Engine | License | GPU | Win | Linux | Best for | Weak spot | Install |
|:-------|:--------|:----|:----|:------|:---------|:----------|:--------|
| [PaddleOCR 3.5](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv5, **PP-OCRv6** Jun 2026, PP-StructureV3, PP-ChatOCRv4) | Apache-2.0 | opt | yes | yes | Best all-round open pipeline. CJK, tables, layout, formula, seal, doc unwarping. Server and mobile tiers | Heavy dependency (paddlepaddle), API churn between 2.x and 3.x, Chinese-first docs | `pip install paddlepaddle paddleocr` (GPU: `paddlepaddle-gpu` from Baidu's index) |
| [RapidOCR 3.x](https://github.com/RapidAI/RapidOCR) | Apache-2.0 | opt | yes | yes | PP-OCR models on ONNX Runtime / OpenVINO / Torch with **no paddle dependency**. 15 MB. Best CPU default in 2026. Supports PP-OCRv6 | No layout/table (use `rapid_layout`, `rapid_table` sister packages) | `pip install rapidocr` (or `rapidocr-onnxruntime`) |
| [EasyOCR 1.7](https://github.com/JaidedAI/EasyOCR) | Apache-2.0 | opt | yes | yes | Three-line prototype, 80+ languages, scene text (CRAFT + CRNN) | No real updates since 2024, 1.5 GB PyTorch install, lower ceiling than Paddle | `pip install easyocr` |
| [docTR](https://github.com/mindee/doctr) (now maintained by t2k) | Apache-2.0 | opt | yes | yes | Clean Python API, page/block/line/word hierarchy, swappable backbones (DBNet, FAST, CRNN, ViTSTR, PARSeq), CER ties VLMs on printed text | English/Latin focus, no CJK to speak of | `pip install "python-doctr[torch]"` |
| [OnnxTR](https://github.com/felixdittrich92/OnnxTR) | Apache-2.0 | opt | yes | yes | docTR models on ONNX Runtime, no torch, 8-bit variants | Same language limits as docTR | `pip install "onnxtr[cpu]"` |
| [MMOCR 1.x](https://github.com/open-mmlab/mmocr) | Apache-2.0 | opt | yes | yes | Research toolbox: DBNet++, FCENet, ABINet, PARSeq, SATRN, KIE (SDMGR) | Steep, OpenMMLab dependency stack, slow-moving | `pip install mmocr` after mmcv/mmdet |
| [OpenOCR](https://github.com/Topdu/OpenOCR) | Apache-2.0 | opt | yes | yes | SVTRv2-based, claims PP-OCRv4-beating accuracy, unified STR benchmark | Younger community | `pip install openocr-python` |
| [Surya (v1 pipeline)](https://github.com/datalab-to/surya) | Apache-2.0 code (check weights) | opt | yes | yes | Detection + layout + reading order + table rec in 90+ languages; Surya 2 is a single VLM (see D) | Slow on CPU | `pip install surya-ocr` |
| [ocrs](https://github.com/robertknight/ocrs) | Apache/MIT | no | yes | yes | Rust library + CLI + WASM, tiny models, embed in native apps | Preview quality, Latin only | `cargo install ocrs-cli` |
| [keras-ocr](https://github.com/faustomorales/keras-ocr) | MIT | opt | yes | yes | CRAFT + CRNN in Keras, teaching code | Unmaintained | `pip install keras-ocr` |
| [ML Kit Text Recognition v2](https://developers.google.com/ml-kit/vision/text-recognition/v2) | Google terms | NPU | Android/iOS | no | On-device mobile OCR, Latin/CJK/Devanagari | Mobile only | Gradle/CocoaPods |

**What to take away:** RapidOCR for CPU boxes today, PaddleOCR when you need structure, docTR when you
want a clean Python object model on English documents. EasyOCR only if a tutorial forces it.

---

## C. Document parsers (layout + OCR + tables + Markdown)

| Tool | License | GPU | Win | Linux | Best for | Weak spot | Install |
|:-----|:--------|:----|:----|:------|:---------|:----------|:--------|
| [OCRmyPDF 17.4](https://github.com/ocrmypdf/OCRmyPDF) | MPL-2.0 | no | yes (pip + deps) | yes | Scanned PDF -> searchable PDF/A with Tesseract. Deskew, clean, rotate, skip-text, sidecar txt, plugin OCR engines | Text only, no Markdown structure | `apt install ocrmypdf` / `pip install ocrmypdf` |
| [Marker v2](https://github.com/datalab-to/marker) | GPL-3.0 (weights: check) | opt | yes | yes | PDF/EPUB/DOCX/images -> Markdown/JSON/HTML with tables, math, images. `--use_llm` upgrades tables and forms | GPU strongly preferred, license for commercial use | `pip install marker-pdf` |
| [MinerU 2.5](https://github.com/opendatalab/MinerU) | AGPL-3.0 | opt | yes (pipeline) | yes | PDF -> Markdown/JSON, two backends: `pipeline` (PP models) and `vlm` (MinerU2.5-1.2B). Strong on academic PDFs, formulas, Chinese | AGPL, vLLM backend Linux only | `pip install "mineru[core]"` |
| [Docling 2.x](https://github.com/docling-project/docling) | MIT | opt | yes | yes | PDF/DOCX/PPTX/HTML/images -> DoclingDocument -> MD/JSON. Pluggable OCR (EasyOCR default, Tesseract, RapidOCR, OnnxTR). Granite-Docling-258M VLM pipeline. Linux Foundation project | Default EasyOCR is the weak link; swap it | `pip install docling` |
| [olmOCR](https://github.com/allenai/olmocr) | Apache-2.0 | yes | WSL/Docker | yes | Batch PDF linearization with olmOCR-2-7B on vLLM, Markdown out, olmOCR-Bench included | 7B model wants 16 GB+ VRAM (FP8 build helps), Linux only | `pip install olmocr[gpu]` |
| [Nougat](https://github.com/facebookresearch/nougat) | MIT | opt | yes | yes | Academic PDF -> Markdown with LaTeX (the original) | Superseded, hallucinates, English arXiv bias | `pip install nougat-ocr` |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) | Apache-2.0 | opt | yes | yes | Partition any file type into elements for RAG; OCR via Tesseract/PaddleOCR | Heavy, hosted product upsell | `pip install "unstructured[all-docs]"` |
| [PyMuPDF4LLM](https://github.com/pymupdf/RAG) | AGPL-3.0 | no | yes | yes | Text-native PDF -> Markdown fast; can call Tesseract for image pages | Not an OCR engine | `pip install pymupdf4llm` |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | MIT | no | yes | yes | Text-native PDF tables and char boxes | No OCR at all | `pip install pdfplumber` |
| [Chunkr](https://github.com/lumina-ai-inc/chunkr) | AGPL-3.0 | opt | Docker | yes | Self-hostable document ingestion API with layout + OCR + chunking | Service-shaped, not a library | Docker compose |
| [LlamaParse](https://www.llamaindex.ai/llamaparse) | commercial | cloud | any | any | Hosted parsing with LLM modes | Cloud, per-page cost | API key |
| [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | GPL-3.0 | no | Docker | yes | Document management with automatic OCRmyPDF on ingest, tags, full-text search | Not a library | Docker compose |

**What to take away:** OCRmyPDF for archives (searchable PDFs), Marker or Docling for LLM ingestion,
MinerU when the PDFs are academic or Chinese, olmOCR when you have a GPU box and a million pages.

---

## D. VLM OCR models (generation 5)

Parameter counts and VRAM are approximate; the VRAM column is bf16 weights plus a working margin at a
1024 px page. Quantized builds (INT8/INT4/FP8) cut it by half to three quarters. Detailed cards, routes,
and the 8 GB fit table are in [07-vlm-document-parsers.md](07-vlm-document-parsers.md).

| Model | Org | Params | VRAM bf16 | License | Output | Notes |
|:------|:----|:------:|:---------:|:--------|:-------|:------|
| [PaddleOCR-VL 1.6](https://github.com/PaddlePaddle/PaddleOCR) | Baidu | 0.9B | ~3 GB | Apache-2.0 | MD/JSON with layout | 1.5 scored 94.5 on OmniDocBench; PP-DocLayoutV3 front end; runs via PaddleOCR, vLLM, SGLang, Transformers |
| [GLM-OCR](https://huggingface.co/zai-org) | Z.ai | 0.9B | ~3 GB | MIT | MD/JSON | Rank 3 on OmniDocBench v1.6 (95.2), the most permissive license in the top three |
| [DeepSeek-OCR-2](https://github.com/deepseek-ai/DeepSeek-OCR-2) | DeepSeek | ~3.4B | ~7.4 GB | MIT | MD | "Visual Causal Flow"; 91.09 on OmniDocBench v1.5; fits an 8 GB card in FP16, comfortable at INT4 |
| [DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-OCR) | DeepSeek | 3B (570M active MoE) | ~7 GB | MIT | MD | "Contexts Optical Compression": 64 to 800 vision tokens per page, Tiny/Small/Base/Large/Gundam modes |
| [dots.ocr](https://github.com/rednote-hilab/dots.ocr) | rednote | 1.7B | ~5 GB | MIT | JSON layout + MD | Single model for layout + text, 100 languages, strong on multilingual |
| [HunyuanOCR](https://github.com/Tencent-Hunyuan/HunyuanOCR) | Tencent | 1B | ~3 GB | Tencent license | MD/JSON, KIE, translation | End-to-end, 100+ languages, released Nov 2025 |
| [Chandra](https://github.com/datalab-to/chandra) | Datalab | 8B (Qwen3-VL) | ~18 GB | Apache-2.0 | MD/HTML/JSON with boxes | 83.1 on olmOCR-Bench (top open score Oct 2025). Too big for 8 GB unquantized; Datalab hosts an API |
| [olmOCR-2-7B](https://huggingface.co/allenai/olmOCR-2-7B-1025) | Allen AI | 7B | ~16 GB (FP8 ~9) | Apache-2.0 | MD | 82.4 on olmOCR-Bench; the olmOCR pipeline's default |
| [Nanonets-OCR2-3B](https://huggingface.co/nanonets/Nanonets-OCR2-3B) | Nanonets | 3B | ~7 GB | Apache-2.0 | MD with tables, LaTeX, checkboxes, signatures, watermarks | Qwen2.5-VL fine-tune; tags semantic elements |
| [LightOnOCR-1B](https://huggingface.co/lightonai/LightOnOCR-1B-1025) | LightOn | 1B | ~3 GB | Apache-2.0 | MD | Very fast; cleaner output than 3B rivals on scanned forms in independent tests |
| [Granite-Docling-258M](https://huggingface.co/ibm-granite/granite-docling-258m) | IBM | 258M | ~1 GB (CPU ok) | Apache-2.0 | DocTags -> MD/JSON | Runs on CPU and Apple MLX; Docling's `--pipeline vlm` default |
| [MinerU2.5-1.2B](https://huggingface.co/opendatalab/MinerU2.5-2509-1.2B) | OpenDataLab | 1.2B | ~4 GB | AGPL-3.0 | MD/JSON | The `vlm` backend of MinerU; 75.2 on olmOCR-Bench |
| [Surya 2](https://github.com/datalab-to/surya) | Datalab | ~650M | ~2.5 GB | Apache-2.0 code | Layout + OCR + tables | Pareto-best under 3B; 5 pages/s on a 5090; handwriting and forms improved over v1 |
| [MonkeyOCR](https://github.com/Yuliang-Liu/MonkeyOCR) | HUST | 1.2B / 3B | 4 to 7 GB | Apache-2.0 | MD/JSON | Structure-Recognition-Relation triplet design |
| [GOT-OCR 2.0](https://github.com/Ucas-HaoranWei/GOT-OCR2.0) | UCAS | 580M | ~2 GB | Apache-2.0 | plain / formatted (MD, LaTeX, TikZ) | In Hugging Face Transformers natively; sheet music, charts, molecules |
| [Florence-2](https://huggingface.co/microsoft/Florence-2-large) | Microsoft | 0.23B / 0.77B | ~2 GB | MIT | text, text+region | `<OCR>` and `<OCR_WITH_REGION>` tasks; generalist |
| [TrOCR](https://huggingface.co/microsoft/trocr-large-handwritten) | Microsoft | 334M / 558M | ~2 GB | MIT | line text | Line-level only; printed, handwritten, and STR checkpoints |
| [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL) 2B/4B/8B/32B | Alibaba | 2B to 32B | 4B q4 ~4 GB, 8B q4 ~6 GB | Apache-2.0 | anything you prompt | DocVQA 96.1 (8B). `ollama run qwen3-vl:8b`. The general-purpose choice |
| [MiniCPM-V 4.5](https://github.com/OpenBMB/MiniCPM-V) | OpenBMB | 8B | q4 ~6 GB | Apache-2.0 (weights: OpenBMB) | anything | Strong OCRBench, 32 languages, Ollama available |
| [Gemma 3 4B/12B](https://ai.google.dev/gemma) | Google | 4B / 12B | q4 4 to 8 GB | Gemma terms | anything | Decent doc reading, weaker on tables than dedicated models |
| [InternVL 3](https://github.com/OpenGVLab/InternVL) | Shanghai AI Lab | 1B to 78B | varies | MIT | anything | Research-grade generalist |
| [Llama 3.2 Vision 11B](https://ollama.com/library/llama3.2-vision) | Meta | 11B | q4 ~8 GB | Llama license | anything | Adequate OCR, not a specialist |

**What to take away:** on an 8 GB card the sensible order is PaddleOCR-VL 1.6, LightOnOCR-1B, dots.ocr,
DeepSeek-OCR-2 (INT4 or FP16 with nothing else loaded), Surya 2, then Qwen3-VL 8B q4 for free-form questions.
Chandra and olmOCR-2 are 16 GB+ models; use the FP8/INT4 builds or a hosted API.

---

## E. Handwriting and historical documents (HTR / ATR)

| Tool | License | GPU | Win | Linux | Best for | Weak spot | Install |
|:-----|:--------|:----|:----|:------|:---------|:----------|:--------|
| [TrOCR](https://github.com/microsoft/unilm/tree/master/trocr) | MIT | opt | yes | yes | Line-level handwriting and print, fine-tunes with HF Trainer | You must segment lines yourself | `pip install transformers` |
| [PyLaia](https://github.com/jpuigcerver/PyLaia) | MIT | opt | yes | yes | CRNN+CTC HTR, fast, trains on small data, integrated LM decoding (Teklia fork) | Needs line segmentation | `pip install pylaia` |
| [Kraken 5](https://kraken.re/) | Apache-2.0 | opt | WSL | yes | Full pipeline: baseline segmentation + recognition, trainable (`ketos`), ALTO/PAGE | Windows | `pip install kraken` |
| [eScriptorium](https://gitlab.com/scripta/escriptorium) | MIT | opt | Docker | yes | Web UI for transcribing, correcting, and training Kraken models on your own corpus | Docker stack | Docker compose |
| [OCR4all](https://github.com/OCR4all/OCR4all) | MIT | opt | Docker | yes | Guided semi-automatic workflow for early printed books, Calamari/Kraken/Tesseract inside | Docker only | Docker |
| [OCR-D](https://ocr-d.de/) | Apache-2.0 | opt | Docker | yes | German national framework of composable processors (binarize, segment, recognize, evaluate) for mass digitization | Complexity | `pip install ocrd` + processors |
| [Transkribus](https://www.transkribus.org/) | commercial (credits) | cloud | any | any | Turnkey HTR platform, huge public model zoo, PyLaia and HTR+ under the hood | Pay per page after free credits | web |
| [Loghi](https://github.com/knaw-huc/loghi) | MIT | yes | Docker | yes | Dutch archives' full HTR stack (Laypa segmentation + Loghi-HTR) | Docker only | Docker |
| [HTR-United](https://htr-united.github.io/) | various | n/a | n/a | n/a | Catalog of open ground-truth datasets for training | not software | browse |
| [Surya 2 / Qwen3-VL](#d-vlm-ocr-models-generation-5) | see D | yes | yes | yes | Modern handwriting without training anything | Historical scripts | see D |

**What to take away:** modern handwriting (notes, forms, letters): start with a VLM. Historical
material or a consistent single hand across thousands of pages: train Kraken or PyLaia on 50 to 200
transcribed lines, or use Transkribus if you want a GUI and do not mind credits.

---

## F. Math, tables, and specialty scripts

| Tool | License | GPU | Best for | Install |
|:-----|:--------|:----|:---------|:--------|
| [pix2tex / LaTeX-OCR](https://github.com/lukas-blecher/LaTeX-OCR) | MIT | opt | Formula crop -> LaTeX, has a GUI and a screenshot mode | `pip install "pix2tex[gui]"` |
| [Texify](https://github.com/VikParuchuri/texify) | GPL-3.0 | opt | Formula/text crop -> Markdown+LaTeX, trained on web math | `pip install texify` |
| [UniMERNet](https://github.com/opendatalab/UniMERNet) | Apache-2.0 | opt | Real-world formula recognition (printed, handwritten, screenshot, noisy), UniMER-1M dataset | repo |
| [Nougat](https://github.com/facebookresearch/nougat) | MIT | opt | Whole academic page with math | `pip install nougat-ocr` |
| [Texo](https://arxiv.org/abs/2602.17189) | research | no | Formula recognition in 20M params | paper |
| [img2table](https://github.com/xavctn/img2table) | MIT | no | Table structure from images/PDFs using OpenCV lines + any OCR (Tesseract, Paddle, EasyOCR, docTR, Azure, AWS) -> pandas/xlsx | `pip install img2table` |
| [Table Transformer (TATR)](https://github.com/microsoft/table-transformer) | MIT | opt | DETR-based table detection + structure recognition (PubTables-1M) | `pip install transformers` |
| [PP-StructureV3](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 | opt | Layout + table (wired and wireless) + formula + seal + chart -> MD/JSON | `paddleocr` |
| [Surya table recognition](https://github.com/datalab-to/surya) | see B | opt | Cell rows/cols from a table crop | `surya_table` |
| [manga-ocr](https://github.com/kha-white/manga-ocr) | Apache-2.0 | opt | Japanese manga speech bubbles, vertical text, furigana | `pip install manga-ocr` |
| [YomiToku](https://github.com/kotaro-kinoshita/yomitoku) | CC BY-NC-SA 4.0 (commercial license available) | opt | Japanese document AI: layout, tables, vertical text | `pip install yomitoku` |
| [Pero-OCR](https://github.com/DCGM/pero-ocr) | BSD-3 | opt | Czech/Central-European print and handwriting, ALTO/PAGE | `pip install pero-ocr` |
| [Tesseract `osd`](03-tesseract-deep-dive.md) | Apache-2.0 | no | Orientation and script detection (0/90/180/270 + script) | ships with Tesseract |

---

## G. OS-native OCR

| Tool | OS | What it is | Access from code | Notes |
|:-----|:---|:-----------|:-----------------|:------|
| [Windows.Media.Ocr](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr) | Windows 10+ | The WinRT OCR API. Languages come from Settings > Language > add language > Optical character recognition feature | Python: [`winocr`](https://pypi.org/project/winocr/). C#/PowerShell: WinRT. | Word boxes, no confidences, fast, good on rendered text |
| [OneOCR](https://github.com/AuroraWright/oneocr) | Windows 11 Snipping Tool | The newer ONNX engine (`oneocr.dll` + `oneocr.onemodel` + `onnxruntime.dll`) used by Snipping Tool "Text actions", Photos, and Phone Link | Python: `pip install oneocr` (copy the 3 files from the ScreenSketch package). C: [b1tg/win11-oneocr](https://github.com/b1tg/win11-oneocr). A [full reimplementation](https://huggingface.co/MattyMroz/oneocr) extracted the 34 ONNX models | Word boxes + confidences + angle. Noticeably better than Windows.Media.Ocr on small fonts |
| [PowerToys Text Extractor](https://learn.microsoft.com/en-us/windows/powertoys/text-extractor) | Windows 10/11 | Win+Shift+T, drag a region, text goes to clipboard. Uses the Windows OCR languages | n/a (hotkey tool) | Install OCR language packs or it only sees English |
| Snipping Tool text actions | Windows 11 | Built-in "Text actions" button on any capture | n/a | OneOCR under the hood |
| [Apple Vision / VisionKit](https://developer.apple.com/documentation/vision/recognizing-text-in-images) | macOS/iOS | `VNRecognizeTextRequest`, Live Text | Swift; Python via `ocrmac` | Excellent on photos; Docling's `ocrmac` engine wraps it |

---

## H. Desktop applications (GUI)

| App | OS | Engine inside | License | Best for |
|:----|:---|:--------------|:--------|:---------|
| [gImageReader](https://github.com/manisandro/gImageReader) | Win, Linux | Tesseract | GPL-3.0 | Batch OCR of scans with a GUI, hOCR editor, spellcheck, PDF output |
| [NormCap](https://github.com/dynobo/normcap) | Win, Linux, macOS | Tesseract (bundled) | GPL-3.0 | Screenshot OCR to clipboard with URL/email detection |
| [OCRFeeder](https://gitlab.gnome.org/GNOME/ocrfeeder) | Linux (GNOME) | Tesseract, Ocrad, GOCR, CuneiForm | GPL-3.0 | Layout-aware OCR to ODT/HTML with an editor |
| [Frog](https://github.com/TenderOwl/Frog) | Linux (GNOME) | Tesseract | MIT | Grab text from screen, video, QR codes; Flatpak |
| [Capture2Text](https://capture2text.sourceforge.net/) | Windows | Tesseract | GPL | Old but loved hotkey OCR; mostly replaced by PowerToys |
| [ShareX](https://getsharex.com/) | Windows | Windows OCR | GPL-3.0 | Screenshot tool with an OCR action in the after-capture chain |
| [Paperwork](https://openpaper.work/) | Linux | Tesseract | GPL-3.0 | Personal document manager with OCR and search |
| [OCRmyPDF GUI wrappers](https://github.com/ocrmypdf/OCRmyPDF/wiki) | any | Tesseract | various | Drag-and-drop front ends; see the wiki list |
| [ABBYY FineReader PDF](https://pdf.abbyy.com/) | Windows, macOS | ABBYY | commercial | Still the best desktop accuracy on complex printed layouts and 200 languages |
| [Adobe Acrobat Pro](https://www.adobe.com/acrobat.html) | Windows, macOS | Adobe | commercial | "Recognize Text" on scans; good enough, everyone has it |
| [Readiris](https://www.irislink.com/) | Windows, macOS | IRIS (Canon) | commercial | Bundled with scanners |
| [Kofax OmniPage](https://www.tungstenautomation.com/products/omnipage) | Windows | OmniPage | commercial | Enterprise batch OCR |

---

## I. PDF and rasterization plumbing

| Tool | Role | Install |
|:-----|:-----|:--------|
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | Detect text layers, render pages to pixmaps at any DPI, insert OCR text layers (bundles Tesseract calls) | `pip install pymupdf` |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) | Chromium's PDFium as a wheel; fast, permissive license rasterizer | `pip install pypdfium2` |
| [pdf2image + Poppler](https://github.com/Belval/pdf2image) | `pdftoppm` wrapper; Windows needs a Poppler build on PATH | `pip install pdf2image`; `apt install poppler-utils` |
| [Ghostscript](https://www.ghostscript.com/) | Rasterize and produce PDF/A; OCRmyPDF dependency | `apt install ghostscript` / Win installer |
| [qpdf](https://qpdf.sourceforge.io/) | Repair, linearize, split; OCRmyPDF dependency | `apt install qpdf` |
| [img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf) | Lossless image -> PDF | `pip install img2pdf` |
| [pikepdf](https://github.com/pikepdf/pikepdf) | Python qpdf binding | `pip install pikepdf` |
| [hocr-tools](https://github.com/ocropus/hocr-tools) | Merge hOCR + image into searchable PDF, evaluate hOCR | `pip install hocr-tools` |

---

## J. Preprocessing and image cleanup

| Tool | Role | Install |
|:-----|:-----|:--------|
| [OpenCV](https://opencv.org/) | Everything: grayscale, thresholds, deskew, morphology, denoise, perspective | `pip install opencv-python` |
| [scikit-image](https://scikit-image.org/) | Sauvola/Niblack thresholds, `rotate`, `denoise_tv` | `pip install scikit-image` |
| [Leptonica](http://www.leptonica.org/) | Tesseract's own image library; exposed through `tesseract -c` params | ships with Tesseract |
| [unpaper](https://github.com/unpaper/unpaper) | Post-scan cleanup: deskew, despeckle, border removal, black-edge fix | `apt install unpaper` (Linux/WSL only) |
| [ScanTailor Advanced](https://github.com/ScanTailor-Advanced/scantailor-advanced) | GUI batch post-processing of book scans: split pages, deskew, dewarp, margins | releases page (Win/Linux) |
| [ImageMagick](https://imagemagick.org/) | CLI resize, `-deskew 40%`, `-lat` adaptive threshold, `textcleaner` script | `winget install ImageMagick.ImageMagick` |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Super-resolution before OCR of tiny text; use with caution | releases |
| [PaddleOCR doc unwarping](https://github.com/PaddlePaddle/PaddleOCR) | UVDoc-based dewarping of curved book photos | `paddleocr` (`use_doc_unwarping=True`) |
| [Four-point perspective](08-preprocessing.md) | DocScanner-style transform for phone photos | OpenCV snippet in 08 |

---

## K. Cloud and API OCR

Pricing (list, Sep 2026 roundups): see [11-cloud-apis.md](11-cloud-apis.md).

| Service | Strength | Read OCR price / 1,000 pages | Structured price |
|:--------|:---------|:----------------------------:|:-----------------|
| [Azure AI Document Intelligence](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence) | Prebuilt invoice/receipt/ID/W-2 models, layout, custom extraction | $1.50 | $10 prebuilt, $30 custom |
| [Google Document AI](https://cloud.google.com/document-ai) | OCR + Form Parser + specialized processors, Vertex integration | $1.50 | $10 to $30 |
| [Google Cloud Vision](https://cloud.google.com/vision) | `TEXT_DETECTION` / `DOCUMENT_TEXT_DETECTION`, scene text, 1,000 free/month | $1.50 | n/a |
| [AWS Textract](https://aws.amazon.com/textract/) | Detect text, Forms, Tables, Queries, Expense, ID | $1.50 | $65 (Forms + Tables) |
| [Mistral OCR 3](https://mistral.ai/) | Flat-rate Markdown OCR, very cheap, multilingual | ~$1 to $2 flat | same |
| [Datalab API](https://www.datalab.to/) | Hosted Marker/Chandra | per page | same |
| [OCR.space](https://ocr.space/) | Free tier API, Tesseract/own engine | free tier, then paid | n/a |
| [OpenAI / Anthropic / Google multimodal](11-cloud-apis.md) | Ask a frontier model to transcribe; expensive per page, best reasoning | token priced | n/a |

---

## L. Browser and JavaScript

| Tool | What |
|:-----|:-----|
| [tesseract.js](https://github.com/naptha/tesseract.js) | Tesseract compiled to WASM, runs in the browser or Node, same traineddata files |
| [Transformers.js](https://huggingface.co/docs/transformers.js) | Run TrOCR, Florence-2, and small VLMs in the browser via ONNX Runtime Web / WebGPU |
| [ocrs WASM](https://github.com/robertknight/ocrs) | The Rust engine's browser build |
| [Scribe.js](https://github.com/scribeocr/scribe.js) | Browser OCR + PDF text layer editor built on tesseract.js |

---

## Counting

Sections A through L list 60+ engines and models and 100+ tools in total. If something you use is
missing, it is either dead (CuneiForm-class), a thin wrapper of something listed, or I missed it.
Add it to [13-link-index.md](13-link-index.md).
