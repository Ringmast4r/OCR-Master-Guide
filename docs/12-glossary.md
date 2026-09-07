# 12. Glossary

[Back to README](../README.md) | Prev: [Cloud APIs](11-cloud-apis.md) | Next: [Link index](13-link-index.md)

One line each. Alphabetical.

| Term | Meaning |
|:-----|:--------|
| **ABINet** | Scene-text recognizer with an explicit language model branch (MMOCR). |
| **ALTO** | Analyzed Layout and Text Object. Library-world XML for OCR output with coordinates; pairs with METS. |
| **ANLS** | Average Normalized Levenshtein Similarity; the DocVQA metric. |
| **ATR** | Automatic Text Recognition; umbrella term for OCR + HTR used in digital humanities. |
| **AWQ / GPTQ / bitsandbytes** | Weight quantization schemes that shrink VLMs to INT4/INT8 for small GPUs. |
| **Baseline** | The line text sits on; Kraken segments by baselines rather than boxes. |
| **Beam search** | Decoding that keeps the top-k partial outputs; used in CTC and LLM decoders. |
| **bf16 / fp16 / fp32** | Numeric precisions; bf16 is the default for VLM inference on modern GPUs. |
| **Binarization** | Converting grayscale to black/white; Otsu (global), adaptive, Sauvola, Niblack. |
| **Bounding box / polygon** | Rectangle or quadrilateral around a detected text region. |
| **CDM** | Character Detection Matching; formula recognition metric used by OmniDocBench. |
| **CER** | Character Error Rate: edits per ground-truth character. |
| **cMER** | Character Match Error Rate; HIPE-OCRepair 2026 metric. |
| **CRAFT** | Character Region Awareness for Text detection; EasyOCR's detector. |
| **CRNN** | Convolutional Recurrent Neural Network; the classic CNN + BiLSTM + CTC recognizer. |
| **CTC** | Connectionist Temporal Classification; loss/decoder that aligns variable-length outputs without segmentation. |
| **DAWG** | Directed Acyclic Word Graph; Tesseract's compressed dictionary format. |
| **DBNet / DBNet++** | Differentiable Binarization text detector; PaddleOCR's and docTR's default. |
| **Deskew** | Rotating a page so text lines are horizontal. |
| **Dewarp** | Flattening curved pages (book spines, phone photos). |
| **DLA** | Document Layout Analysis: regions and their types. |
| **DocTags** | IBM's compact markup emitted by Granite-Docling; converted to Markdown/JSON by Docling. |
| **DocVQA** | Document Visual Question Answering benchmark. |
| **Donut** | Document Understanding Transformer; OCR-free KIE model (Clova). |
| **DPI** | Dots per inch. 300 is the OCR norm for 10 to 12 pt text. |
| **FAST** | Fast text detector used by docTR. |
| **FP8** | 8-bit float; olmOCR ships FP8 builds that halve VRAM. |
| **FUNSD / CORD / SROIE** | Forms, receipts, invoices KIE benchmarks. |
| **Ground truth (GT)** | The correct transcription used to score or train. |
| **hOCR** | HTML microformat for OCR output with boxes and confidences. |
| **HTR** | Handwritten Text Recognition. |
| **IAM** | The standard English handwriting dataset. |
| **ICDAR** | International Conference on Document Analysis and Recognition; hosts the Robust Reading competitions. |
| **IoU** | Intersection over Union; box overlap metric. |
| **KenLM** | Fast n-gram language model toolkit; used by PyLaia and Calamari for LM decoding. |
| **KIE** | Key Information Extraction: fields from documents. |
| **LayoutLM** | Microsoft's text + layout + image transformers for KIE (v1 to v3). |
| **Leptonica** | Tesseract's C image library. |
| **Levenshtein distance** | Minimum single-character edits between two strings. |
| **Line segmentation** | Splitting a region into text lines; input to line recognizers. |
| **LoRA / QLoRA** | Low-rank adapters for cheap fine-tuning; QLoRA adds 4-bit base weights. |
| **LSTM** | Long Short-Term Memory recurrent network; Tesseract 4/5's recognizer. |
| **METS** | Metadata Encoding and Transmission Standard; wraps ALTO in library workflows and OCR-D. |
| **MER** | Mathematical Expression Recognition. |
| **NaViT** | Native-resolution ViT that accepts variable image sizes; PaddleOCR-VL's encoder style. |
| **NFC** | Unicode normalization form; apply before scoring CER. |
| **OCR** | Optical Character Recognition. |
| **OEM** | Tesseract OCR Engine Mode (0 legacy, 1 LSTM, 2 both, 3 default). |
| **OmniDocBench** | OpenDataLab's end-to-end document parsing benchmark. |
| **olmOCR-Bench** | Allen AI's unit-test benchmark over real PDFs. |
| **ONNX / ONNX Runtime** | Portable model format and its runtime; RapidOCR, OnnxTR, OneOCR use it. |
| **OpenVINO** | Intel's inference runtime; RapidOCR backend. |
| **OSD** | Orientation and Script Detection (Tesseract `osd.traineddata`, `--psm 0`). |
| **Otsu** | Global threshold that maximizes between-class variance. |
| **PAGE-XML** | PRImA's layout + text ground-truth XML; eScriptorium, Kraken, OCR-D, Transkribus. |
| **PARSeq** | Permuted Autoregressive Sequence recognizer; strong scene-text model in docTR and MMOCR. |
| **PDF/A** | Archival PDF profile; OCRmyPDF's default output type. |
| **Perceptual hash (pHash)** | Image fingerprint for deduplicating video frames. |
| **PP-OCR / PP-Structure / PP-DocLayout** | PaddleOCR's model families for text, document structure, layout. |
| **PSM** | Tesseract Page Segmentation Mode (0 to 13). |
| **Reading order** | Sequence of regions for linear text. |
| **ROVER** | Recognizer Output Voting Error Reduction; ensemble alignment + vote. |
| **Sauvola** | Local adaptive threshold robust to degraded documents. |
| **Searchable PDF / sandwich PDF** | Image page with invisible text layer. |
| **SGLang** | Fast LLM/VLM serving framework, alternative to vLLM. |
| **STR** | Scene Text Recognition. |
| **SVTR / SVTRv2** | Single Visual model for scene Text Recognition; PP-OCRv4+/OpenOCR recognizer. |
| **TEDS** | Tree Edit Distance Similarity; table structure metric. |
| **tessdata / _best / _fast** | Tesseract model repositories: combined, float LSTM, integer LSTM. |
| **traineddata** | Tesseract model file. |
| **TrOCR** | Transformer OCR (ViT encoder + text decoder) for lines. |
| **Unicharset** | Tesseract's character set definition inside a model. |
| **ViT** | Vision Transformer. |
| **VLM** | Vision-Language Model. |
| **vLLM** | High-throughput LLM/VLM inference server with an OpenAI-compatible API. |
| **WER** | Word Error Rate. |
| **WinRT** | Windows Runtime; `Windows.Media.Ocr` lives here. |
| **WSL2** | Windows Subsystem for Linux 2, with GPU passthrough. |
| **x-height** | Height of a lowercase x; the size that matters for OCR (20+ px). |
