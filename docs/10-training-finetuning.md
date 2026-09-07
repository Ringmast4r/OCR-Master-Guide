# 10. Training and fine-tuning

[Back to README](../README.md) | Prev: [Evaluation](09-evaluation.md) | Next: [Cloud APIs](11-cloud-apis.md)

When the stock models are wrong on *your* material in a *consistent* way, training beats preprocessing.
This guide ranks the options by effort, then walks each one. Ground-truth format across all of them is the
same: a line image plus its exact transcription.

---

## Decide first

| Situation | Do this | Effort |
|:----------|:--------|:------:|
| Stock engine is at 97 percent and errors are random | Preprocess, change engine, ensemble ([06](06-pairing-recipes.md)) | hours |
| One typeface (receipts, ledgers, a proprietary font) | Fine-tune Tesseract from `tessdata_best` | a day |
| One hand or one historical print run, thousands of pages | Kraken or PyLaia trained from scratch or from a Zenodo model | days |
| Scene text / photos in a narrow domain (plates, meters, labels) | Fine-tune PaddleOCR recognition (PP-OCRv5 rec) or PARSeq | days |
| Handwriting lines, modern | Fine-tune TrOCR with HF Trainer | a day with a GPU |
| Layout, tables, formulas on a new document family | Fine-tune a small VLM (PaddleOCR-VL, Qwen3-VL 2B/4B) with LLaMA-Factory or Unsloth | days, needs a 16 GB+ GPU or QLoRA |
| Fewer than 30 labeled lines | Do not train. Prompt a VLM, or collect more data | |

Ground truth is the bottleneck every time. Build it with the afternoon method in [09](09-evaluation.md) and keep
it under version control.

---

## Synthetic data (before you label anything)

If you own the font or can render the text, generate thousands of lines for free:

| Tool | What | Install |
|:-----|:-----|:--------|
| [text2image](https://tesseract-ocr.github.io/tessdoc/tess4/TrainingTesseract-4.00.html) (Tesseract) | Render text lines with a font list, degrade, output box/tiff pairs | ships with Tesseract training tools |
| [TextRecognitionDataGenerator (trdg)](https://github.com/Belval/TextRecognitionDataGenerator) | Fonts, backgrounds, blur, skew, distortion; outputs `label.txt` + images | `pip install trdg` |
| [SynthTIGER](https://github.com/clovaai/synthtiger) | Clova's scene-text synthesizer used to train PaddleOCR-class recognizers | `pip install synthtiger` |
| [text_renderer](https://github.com/oh-my-ocr/text_renderer) | PaddleOCR-oriented renderer, CJK friendly | repo |
| [augraphy](https://github.com/sparkfish/augraphy) | Document degradation: ink bleed, folds, scanner noise, stains | `pip install augraphy` |
| [SynthDoG](https://github.com/clovaai/donut/tree/master/synthdog) | Synthetic document pages for Donut/VLM training | repo |

Mix synthetic 80 / real 20 and validate only on real.

---

## 1. Tesseract (tesstrain)

Covered in detail in [03](03-tesseract-deep-dive.md#fine-tuning-tesseract-when-and-how). Summary:

```bash
git clone https://github.com/tesseract-ocr/tesstrain && cd tesstrain
mkdir -p data/myfont-ground-truth      # 0001.png + 0001.gt.txt ...
make tesseract-langdata
wget -P data https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata
make training MODEL_NAME=myfont START_MODEL=eng TESSDATA=data MAX_ITERATIONS=5000 LEARNING_RATE=0.0001
make plot MODEL_NAME=myfont             # CER curve
```

Windows: run it in WSL2. Tips: `PSM=13` in the Makefile for pre-cut lines; lines 20 to 60 px x-height; if the
new model regresses on general text you over-trained, lower `MAX_ITERATIONS` or add generic lines to the set.
Replacing the character set (new symbols): `make training` handles a new unicharset automatically when the
`.gt.txt` files contain them, but training from `eng` with a very different alphabet is slower than starting from
the closest script model (`script/Latin`).

---

## 2. Kraken (ketos)

The most complete open training toolkit for historical print and handwriting. Linux/macOS/WSL2.

```bash
pip install kraken
# Ground truth as PAGE-XML or ALTO with baselines + transcriptions (eScriptorium exports this), or line images + .gt.txt
# Segmentation model (baselines) if the layout is unusual:
ketos segtrain -o seg -f page data/*.xml
# Recognition from scratch:
ketos train -f page -o mymodel --device cuda:0 data/*.xml
# Fine-tune a public model (recommended):
kraken get 10.5281/zenodo.7933402                   # example: a public Latin print model DOI, browse the Zenodo community
ketos train -f page -i model.mlmodel --resize union -o mymodel data/*.xml
# Evaluate
ketos test -m mymodel_best.mlmodel -f page test/*.xml
# Use
kraken -i page.png out.txt segment -bl ocr -m mymodel_best.mlmodel
```

`--resize union` keeps the old alphabet and adds yours; `--resize new` replaces it. 50 to 200 lines fine-tunes a
public model; 1,000+ lines trains from scratch. eScriptorium wraps all of this in a browser with a transcription UI.

---

## 3. PyLaia

CRNN + CTC, fast to train, strong on handwriting, used inside Transkribus and Arkindex. Teklia maintains the fork.

```bash
pip install pylaia
# Data: line images + a text file "image_id transcription" (space-separated symbols) + a symbol table
pylaia-htr-create-model --fixed_input_height 128 --common.experiment_dirname exp syms.txt
pylaia-htr-train-ctc --common.experiment_dirname exp --data.batch_size 16 --trainer.gpus 1 syms.txt [img_dirs] train.txt val.txt
pylaia-htr-decode-ctc --common.experiment_dirname exp syms.txt [img_dirs] test_ids.txt
```

Add a language model at decode time (`--decode.use_language_model true` with a KenLM ARPA file) for a few points of CER.

---

## 4. PaddleOCR (detection and recognition)

Fine-tune PP-OCRv5 recognition on a new domain (plates, meters, product labels, a language variant):

```bash
git clone https://github.com/PaddlePaddle/PaddleOCR && cd PaddleOCR
pip install -r requirements.txt
# Download the pretrained rec model from the PP-OCRv5 model list in docs/
# Data: train_list.txt lines of "path\ttranscription"
python tools/train.py -c configs/rec/PP-OCRv5/PP-OCRv5_server_rec.yml \
    -o Global.pretrained_model=./pretrain/PP-OCRv5_server_rec_pretrained \
       Train.dataset.data_dir=./data Train.dataset.label_file_list=[./data/train_list.txt] \
       Eval.dataset.data_dir=./data Eval.dataset.label_file_list=[./data/val_list.txt] \
       Global.character_dict_path=./ppocr/utils/dict/my_dict.txt Global.epoch_num=50
python tools/export_model.py -c ... -o Global.pretrained_model=./output/best_accuracy Global.save_inference_dir=./inference/my_rec
```

Detection (`configs/det/PP-OCRv5/`) trains on polygon labels from [PPOCRLabel](https://github.com/PFCCLab/PPOCRLabel).
PaddleOCR 3.x also fine-tunes through [PaddleX](https://github.com/PaddlePaddle/PaddleX) pipelines with a YAML per
task, which is easier than the raw scripts. Export the result to ONNX with `paddle2onnx` and run it in RapidOCR.

---

## 5. TrOCR (Hugging Face)

```python
from datasets import load_dataset
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer, Seq2SeqTrainingArguments, default_data_collator
proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
model.config.decoder_start_token_id = proc.tokenizer.cls_token_id
model.config.pad_token_id = proc.tokenizer.pad_token_id
model.config.eos_token_id = proc.tokenizer.sep_token_id

ds = load_dataset("imagefolder", data_dir="lines/")          # metadata.jsonl with file_name + text
def prep(b):
    px = proc(images=b["image"], return_tensors="pt").pixel_values
    lab = proc.tokenizer(b["text"], padding="max_length", max_length=64, truncation=True).input_ids
    lab = [[t if t != proc.tokenizer.pad_token_id else -100 for t in l] for l in lab]
    return {"pixel_values": px, "labels": lab}
ds = ds.map(prep, batched=True, remove_columns=ds["train"].column_names)

args = Seq2SeqTrainingArguments("trocr-ft", per_device_train_batch_size=8, num_train_epochs=5, learning_rate=5e-5,
                                fp16=True, eval_strategy="epoch", save_strategy="epoch", predict_with_generate=True)
Seq2SeqTrainer(model=model, args=args, train_dataset=ds["train"], eval_dataset=ds["validation"],
               data_collator=default_data_collator, processing_class=proc.image_processor).train()
```

`trocr-base` fits an 8 GB card at batch 8 with fp16; `trocr-large` needs gradient checkpointing or batch 2.
Compute CER on the validation set with jiwer in a `compute_metrics` callback.

---

## 6. Small VLMs (LoRA / QLoRA)

For layout-heavy documents where you need the Markdown structure adapted (a form family, a catalog format):

| Framework | Models | Notes |
|:----------|:-------|:------|
| [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) | Qwen2.5-VL, Qwen3-VL, InternVL, MiniCPM-V, PaddleOCR-VL (via HF) | YAML-driven, LoRA/QLoRA, Windows and Linux |
| [Unsloth](https://github.com/unslothai/unsloth) | Qwen2.5-VL, Qwen3-VL, Gemma 3, Pixtral | Fastest, lowest VRAM; QLoRA of a 4B fits 8 GB at small batch |
| [Hugging Face TRL](https://github.com/huggingface/trl) | Any `AutoModelForImageTextToText` | `SFTTrainer` with image messages |
| [ms-swift](https://github.com/modelscope/ms-swift) | Everything Chinese labs release first (GLM-OCR, dots.ocr, MinerU) | Linux |

Data: `{"messages": [{"role": "user", "content": [{"type": "image", "image": "p.png"}, {"type": "text", "text": "Convert to Markdown."}]}, {"role": "assistant", "content": "...markdown..."}]}` per page.
200 to 2,000 pages of high-quality Markdown ground truth moves a 1B to 4B model a long way; generate drafts with a
big model, correct by hand, train the small one (distillation).

---

## 7. Layout and detection models

| Need | Train this | Data format |
|:-----|:-----------|:------------|
| New region types (stamp, signature, handwritten note) | YOLO (Ultralytics) or PP-DocLayout via PaddleX | COCO boxes |
| Better text detection on a domain | PaddleOCR DBNet (`configs/det`) or MMOCR DBNet++ | polygons |
| Table structure | PP-StructureV3 table models via PaddleX, or TableFormer (Docling) | HTML cells |
| Baselines for manuscripts | Kraken `ketos segtrain` | PAGE-XML |

---

## Recipes for common training mistakes

| Symptom | Cause | Fix |
|:--------|:------|:----|
| CER goes down on train, up on val | Overfitting a tiny set | More data, fewer iterations, augment (augraphy), early stop on val CER |
| New model reads the new font but forgot everything else | Catastrophic forgetting | Mix 20 to 50 percent generic lines into training |
| Tesseract: `Compute CTC targets failed` | Ground truth has characters not in the unicharset or lines too short/long | Check `.gt.txt` for stray characters, split long lines |
| Kraken: alphabet mismatch on fine-tune | Used `--resize new` | `--resize union` |
| Trained on binarized lines, deployed on color | Train/serve mismatch | Preprocess identically in both places |
| VLM fine-tune outputs stop early or loop | Wrong chat template or missing EOS in labels | Use the model's own template via the framework, verify one sample decodes |
