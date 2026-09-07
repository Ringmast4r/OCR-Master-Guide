# 07. VLM document parsers

[Back to README](../README.md) | Prev: [Pairing recipes](06-pairing-recipes.md) | Next: [Preprocessing](08-preprocessing.md)

The generation-5 models: one network reads a page and writes Markdown. This guide covers what they are,
how to run each one on Windows and Linux, what fits an 8 GB card, and how to keep them honest.

---

## How they work (enough to reason about them)

```
 page image  ->  vision encoder  ->  N visual tokens  ->  LLM decoder  ->  Markdown / HTML / JSON / DocTags
 (1024-1600px)  (ViT / NaViT /       (64 to 4000+)        (0.3B to 8B)
                 SAM+CLIP hybrid)
```

Three design axes explain every model in the table:

1. **Token budget.** DeepSeek-OCR's whole pitch is compressing a page into 64 to 800 visual tokens ("optical
   compression") so the decoder does little work. PaddleOCR-VL uses a NaViT-style dynamic-resolution encoder.
   olmOCR and Chandra sit on Qwen-VL encoders that spend thousands of tokens on a dense page. Fewer tokens = faster
   and cheaper, more tokens = better small text.
2. **Decoder size.** 0.3B (Granite-Docling), 0.9B (PaddleOCR-VL, GLM-OCR), 1B (LightOnOCR, HunyuanOCR),
   1.7B (dots.ocr), 3B (DeepSeek-OCR, Nanonets), 7B to 8B (olmOCR-2, Chandra). Below 2B they fit anywhere;
   above 7B they need 16 GB or quantization.
3. **Layout front end.** PaddleOCR-VL and MinerU run a separate layout detector first and OCR region by region
   (fewer hallucinations, better reading order on wild layouts). dots.ocr, DeepSeek-OCR, olmOCR, Chandra do the
   whole page in one shot (simpler, occasionally drops a footnote).

---

## Model cards

| Model | Params | VRAM (bf16, 1 page) | Fits 8 GB? | Windows native route | Linux route | Output | Leaderboard signal |
|:------|:------:|:-------------------:|:----------:|:---------------------|:------------|:-------|:-------------------|
| [PaddleOCR-VL 1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL) | 0.9B | ~3 GB | yes | `paddleocr` (`PaddleOCRVL()`), Transformers | + vLLM, SGLang | MD, JSON, layout boxes | v1.5: 94.5 OmniDocBench (top tier) |
| [GLM-OCR](https://huggingface.co/zai-org) | ~1B class | ~3 GB | yes | Transformers | + vLLM | MD/JSON | Led OmniDocBench spring 2026 roundups |
| [DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2) | ~3.4B | ~7.4 GB FP16 | tight; INT4 comfortable | Transformers (`trust_remote_code`) | vLLM recipe | MD, grounding boxes | 91.09 OmniDocBench v1.5 |
| [DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) | 3B MoE (570M active) | ~7 GB | tight | Transformers | vLLM | MD | Strong at 100 to 400 tokens/page |
| [dots.ocr](https://huggingface.co/rednote-hilab/dots.ocr) | 1.7B | ~5 GB | yes | Transformers | vLLM | JSON layout + MD | Top multilingual on OmniDocBench at release |
| [HunyuanOCR](https://huggingface.co/tencent/HunyuanOCR) | 1B | ~3 GB | yes | Transformers | vLLM | MD, JSON, KIE, subtitle, translation | Competitive sub-1B |
| [LightOnOCR-1B](https://huggingface.co/lightonai/LightOnOCR-1B-1025) | 1B | ~3 GB | yes | Transformers | vLLM (fast) | MD | Beat 3B rivals on scanned forms in independent tests |
| [Granite-Docling-258M](https://huggingface.co/ibm-granite/granite-docling-258m) | 0.26B | ~1 GB, CPU ok | yes | Docling `--pipeline vlm`, Transformers, MLX | same | DocTags -> MD/JSON | Layout-faithful, small |
| [Nanonets-OCR2-3B](https://huggingface.co/nanonets/Nanonets-OCR2-3B) | 3B | ~7 GB | tight; INT4 ok | Transformers | vLLM | MD with semantic tags (signature, watermark, checkbox, table, LaTeX) | 69.5 olmOCR-Bench |
| [MinerU2.5-1.2B](https://huggingface.co/opendatalab/MinerU2.5-2509-1.2B) | 1.2B | ~4 GB | yes | `mineru -b vlm-transformers` | `-b vlm-vllm-engine` | MD/JSON | 75.2 olmOCR-Bench |
| [Surya 2](https://github.com/datalab-to/surya) | ~0.65B | ~2.5 GB | yes | `surya_ocr`, `surya_layout`, `surya_table` | same | boxes, layout, tables | Pareto-best under 3B (Datalab) |
| [MonkeyOCR](https://huggingface.co/echo840/MonkeyOCR) | 1.2B / 3B | 4 to 7 GB | yes (1.2B) | Transformers | vLLM/LMDeploy | MD/JSON | Strong on Chinese/English docs |
| [olmOCR-2-7B](https://huggingface.co/allenai/olmOCR-2-7B-1025) | 7B | ~16 GB (FP8 ~9) | no (FP8 marginal) | n/a (WSL2) | `olmocr.pipeline` on vLLM | MD | 82.4 olmOCR-Bench |
| [Chandra](https://huggingface.co/datalab-to/chandra) | 8B | ~18 GB | no unquantized | Transformers with 4-bit bitsandbytes | vLLM | MD/HTML/JSON + boxes | 83.1 olmOCR-Bench |
| [GOT-OCR 2.0](https://huggingface.co/stepfun-ai/GOT-OCR-2.0-hf) | 0.58B | ~2 GB | yes | Transformers (native `GotOcr2` class) | same | plain, formatted, LaTeX, TikZ | Older but tiny |
| [Florence-2 large](https://huggingface.co/microsoft/Florence-2-large) | 0.77B | ~2 GB | yes | Transformers | same | text, text+regions | Generalist |
| [Qwen3-VL 4B/8B](https://ollama.com/library/qwen3-vl) | 4B/8B | q4: 4 / 6 GB | yes | Ollama, LM Studio, Transformers | + vLLM | free-form | DocVQA 95.3 / 96.1 |
| [MiniCPM-V 4.5](https://ollama.com/library/minicpm-v) | 8B | q4 ~6 GB | yes | Ollama | + vLLM | free-form | Strong OCRBench |
| [Gemma 3 4B](https://ollama.com/library/gemma3) | 4B | q4 ~4 GB | yes | Ollama | same | free-form | Adequate |
| [Mistral OCR 3](https://docs.mistral.ai/) | API | n/a | n/a | HTTP | HTTP | MD + images | Cheap, strong |

Numbers are from model cards, the vLLM recipes site, and the roundups listed in [13](13-link-index.md).
VRAM includes KV cache for one page at default resolution; batch inference needs more.

---

## VRAM fit table (8 GB card)

| Want | Load this | Precision | Headroom | Notes |
|:-----|:----------|:----------|:---------|:------|
| Best accuracy per GB | PaddleOCR-VL 1.6 | bf16 | ~5 GB free | Layout front end reduces hallucination; runs batch of 4 pages |
| Fastest | LightOnOCR-1B | bf16 | ~5 GB | Simple prompt, Markdown out |
| Multilingual layout JSON | dots.ocr | bf16 | ~3 GB | Set `max_pixels` down if OOM |
| DeepSeek-OCR-2 | DeepSeek-OCR-2 | bf16, nothing else on the GPU | <1 GB | Close browser GPU accel; or use an INT4/AWQ community build |
| Tables/forms with tags | Nanonets-OCR2-3B | 4-bit (bitsandbytes) | ~3 GB | bf16 is 7 GB and will OOM on long pages |
| Free-form Q and A over a page | Qwen3-VL 8B | q4_K_M (Ollama) | ~2 GB | Or 4B for more headroom |
| CPU only | Granite-Docling-258M, RapidOCR | fp32 | n/a | Granite is slow on CPU but works |
| Do not try | olmOCR-2-7B bf16, Chandra bf16 | | | Use FP8/INT4 builds or the hosted APIs |

`nvidia-smi` before you start: Windows desktop compositing and a browser can hold 1 to 2 GB.

---

## Routes

### Route A: Transformers (Windows and Linux, simplest)

```python
# Generic pattern; each model's card has the exact processor/prompt. Example: LightOnOCR
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
mid = "lightonai/LightOnOCR-1B-1025"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, torch_dtype=torch.bfloat16, device_map="cuda")
img = Image.open("page.png").convert("RGB")
msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": "Convert this page to Markdown."}]}]
inputs = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
out = model.generate(**inputs, max_new_tokens=4096, do_sample=False)
print(proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0])
```

Models with custom code (DeepSeek-OCR, dots.ocr, older PaddleOCR-VL revisions) need `trust_remote_code=True` and
follow their own `model.infer(...)` helpers; copy from the card.

4-bit on Windows: `pip install bitsandbytes` and `quantization_config=BitsAndBytesConfig(load_in_4bit=True)`.

### Route B: the project's own CLI (PaddleOCR-VL, MinerU, Surya, Docling)

```bash
paddleocr doc_parser -i page.png --use_doc_orientation_classify False      # PaddleOCR-VL pipeline
mineru -p paper.pdf -o out -b vlm-transformers
surya_ocr page.png --output_dir out
docling page.pdf --pipeline vlm --vlm-model granite_docling --to md
```

### Route C: vLLM / SGLang server (Linux, WSL2, Docker; batch throughput)

```bash
vllm serve PaddlePaddle/PaddleOCR-VL --port 8000
vllm serve lightonai/LightOnOCR-1B-1025 --port 8000 --limit-mm-per-prompt image=1
vllm serve rednote-hilab/dots.ocr --port 8000 --trust-remote-code
```

Send OpenAI-format chat requests with a base64 image. vLLM batches concurrent requests; use 8 to 32 workers.
Every model has a page at [recipes.vllm.ai](https://recipes.vllm.ai/).

### Route D: Ollama (Windows/Linux/macOS, chat models)

```bash
ollama pull qwen3-vl:8b
ollama pull minicpm-v
```

Ollama runs general VLMs, not the dedicated document parsers (as of mid-2026 no PaddleOCR-VL or DeepSeek-OCR in
the Ollama library; check `ollama.com/search?q=ocr` since community GGUF conversions appear). For document
parsing use A, B, or C.

### Route E: olmOCR pipeline (Linux/WSL2, GPU, batch PDFs)

```bash
pip install "olmocr[gpu]"
python -m olmocr.pipeline ./workspace --markdown --pdfs docs/*.pdf --model allenai/olmOCR-2-7B-1025-FP8
```

Handles rasterization, prompting with page metadata, retries on malformed output, and resumable work queues.
Needs 12 GB+ for the FP8 model in practice; on the 8 GB card point `--model` at a smaller vLLM-served model
or run it on a rented GPU.

---

## Prompting document models

Dedicated parsers take fixed prompts; chat VLMs need instruction. What works:

```
Transcribe this page exactly as Markdown.
- Preserve reading order, headings, lists, and paragraph breaks.
- Render tables as Markdown tables; render equations as LaTeX in $...$ or $$...$$.
- Do not summarize, translate, correct spelling, or add commentary.
- If a word is unreadable, write [?].
- Output only the Markdown.
```

Add `Return JSON with keys ...` only after you have the raw transcription; asking for extraction and
transcription in one shot increases hallucination.

---

## Keeping VLMs honest

| Risk | Mitigation |
|:-----|:-----------|
| Invented words in smudged regions | Diff against RapidOCR/Tesseract (recipe 13); ask for `[?]` markers |
| Silent spelling normalization | Forbid it in the prompt; for archival use a classical engine |
| Dropped footnotes/headers | Use a layout-first model (PaddleOCR-VL, MinerU) or a layout detector + region OCR |
| Repetition loops on blank/near-blank pages | `repetition_penalty=1.05`, `max_new_tokens` cap, skip pages with no ink (OpenCV ink ratio) |
| Table cells merged or shifted | TEDS check on a sample; Marker `--use_llm`; PP-StructureV3 for wired tables |
| Wrong reading order in multi-column | Layout-first models; Marker/Docling handle columns explicitly |
| Nondeterminism | `do_sample=False`, temperature 0; fix seeds in vLLM |
| Resolution too low for small text | Increase `max_pixels` / image long side to 1536 to 2048; DeepSeek "Gundam" mode tiles |
| Cost/time blowup on long docs | Skip text-native pages, downscale to 1024 px, batch |

---

## Benchmarks to read before choosing

- **OmniDocBench v1.7** (OpenDataLab): end-to-end document parsing, English + Chinese, text/tables/formulas/reading order. The one Chinese labs optimize for. [github.com/opendatalab/OmniDocBench](https://github.com/opendatalab/OmniDocBench)
- **olmOCR-Bench** (Allen AI): 7,000+ unit tests over real PDFs (does the output contain X, is table cell Y right). The one US labs optimize for. [github.com/allenai/olmocr](https://github.com/allenai/olmocr)
- **OCRBench v2**: VLM-oriented text recognition + reasoning.
- **IDP Leaderboard** (Nanonets): [benchmarking.nanonets.com](https://benchmarking.nanonets.com/benchmarks)

How to run your own: [09-evaluation.md](09-evaluation.md).
