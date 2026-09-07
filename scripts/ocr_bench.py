#!/usr/bin/env python3
"""ocr_bench.py: run every OCR engine you have installed on one image and compare.

    python scripts/ocr_bench.py samples/clean_300dpi.png --gt samples/ground_truth.txt
    python scripts/ocr_bench.py page.png --engines tesseract,rapidocr --save out/
    python scripts/ocr_bench.py --list

Engines are probed by import. Missing ones are reported as "not installed" and skipped.
CER is computed against --gt after Unicode NFC + whitespace normalization (case kept).
Timing includes model load on the first call, which is what you feel in a script.
"""
import argparse
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

# ----------------------------------------------------------------------------- helpers

def find_tesseract():
    exe = shutil.which("tesseract")
    if exe:
        return exe
    if platform.system() == "Windows":
        for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")):
            if os.path.exists(p):
                return p
    return None


def normalize(s):
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()


def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref, hyp):
    ref, hyp = normalize(ref), normalize(hyp)
    if not ref:
        return float("nan")
    return levenshtein(ref, hyp) / len(ref)


def wer(ref, hyp):
    r, h = normalize(ref).split(), normalize(hyp).split()
    if not r:
        return float("nan")
    return levenshtein(r, h) / len(r)


def have(mod):
    return importlib.util.find_spec(mod) is not None


def gpu_available():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


ENGINES = {}


def engine(name, needs, platforms=None):
    def deco(fn):
        ENGINES[name] = {"needs": needs, "fn": fn, "platforms": platforms}
        return fn
    return deco

# ----------------------------------------------------------------------------- engines

@engine("tesseract", "pytesseract")
def run_tesseract(path):
    import pytesseract
    exe = find_tesseract()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
    return pytesseract.image_to_string(path, config="--oem 1 --psm 3")


@engine("tesseract-psm6", "pytesseract")
def run_tesseract_psm6(path):
    import pytesseract
    exe = find_tesseract()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
    return pytesseract.image_to_string(path, config="--oem 1 --psm 6")


@engine("tesseract-psm6-2x", "pytesseract")
def run_tesseract_psm6_2x(path):
    """The screenshot fix: 2x cubic upscale, grayscale, PSM 6."""
    import cv2
    import pytesseract
    exe = find_tesseract()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
    g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return pytesseract.image_to_string(g, config="--oem 1 --psm 6 -c user_defined_dpi=300")


@engine("rapidocr", "rapidocr")
def run_rapidocr(path):
    from rapidocr import RapidOCR
    r = RapidOCR()(path)
    return "\n".join(r.txts or [])


@engine("rapidocr-onnxruntime", "rapidocr_onnxruntime")
def run_rapidocr_ort(path):
    from rapidocr_onnxruntime import RapidOCR
    res, _ = RapidOCR()(path)
    return "\n".join(x[1] for x in (res or []))


@engine("easyocr", "easyocr")
def run_easyocr(path):
    import easyocr
    reader = easyocr.Reader(["en"], gpu=gpu_available(), verbose=False)
    return "\n".join(reader.readtext(path, detail=0, paragraph=False))


@engine("paddleocr", "paddleocr")
def run_paddleocr(path):
    from paddleocr import PaddleOCR
    try:  # 3.x
        ocr = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False,
                        use_textline_orientation=False, lang="en")
        lines = []
        for r in ocr.predict(path):
            texts = None
            try:
                texts = r["rec_texts"]
            except Exception:
                pass
            if texts is None:
                j = getattr(r, "json", None)
                if isinstance(j, dict):
                    texts = j.get("res", j).get("rec_texts", [])
            lines += list(texts or [])
        return "\n".join(lines)
    except TypeError:  # 2.x
        ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
        out = ocr.ocr(path, cls=False) or []
        return "\n".join(item[1][0] for page in out for item in (page or []))


@engine("doctr", "doctr")
def run_doctr(path):
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    model = ocr_predictor(pretrained=True)
    return model(DocumentFile.from_images(path)).render()


@engine("onnxtr", "onnxtr")
def run_onnxtr(path):
    from onnxtr.io import DocumentFile
    from onnxtr.models import ocr_predictor
    model = ocr_predictor()
    return model(DocumentFile.from_images(path)).render()


@engine("surya", "surya")
def run_surya(path):
    """Uses the surya_ocr CLI because the Python API has changed across 0.x releases."""
    import json
    exe = shutil.which("surya_ocr")
    if not exe:
        raise RuntimeError("surya_ocr CLI not on PATH")
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([exe, path, "--output_dir", td], check=True, capture_output=True)
        found = []
        for root, _, files in os.walk(td):
            for f in files:
                if f == "results.json":
                    found.append(os.path.join(root, f))
        if not found:
            raise RuntimeError("surya produced no results.json")
        data = json.load(open(found[0], encoding="utf-8"))
        lines = []
        for _, pages in data.items():
            for page in pages:
                for tl in page.get("text_lines", []):
                    lines.append(tl.get("text", ""))
        return "\n".join(lines)


@engine("winocr", "winocr", platforms=("Windows",))
def run_winocr(path):
    import winocr
    from PIL import Image
    return winocr.recognize_pil_sync(Image.open(path).convert("RGB"), "en")["text"]


@engine("oneocr", "oneocr", platforms=("Windows",))
def run_oneocr(path):
    import oneocr
    from PIL import Image
    return oneocr.OcrEngine().recognize_pil(Image.open(path).convert("RGB"))["text"]


@engine("ollama-qwen3-vl", "ollama")
def run_ollama_qwen3vl(path):
    """Only runs if the model is pulled: ollama pull qwen3-vl:8b"""
    import ollama
    model = os.environ.get("OCR_BENCH_OLLAMA_MODEL", "qwen3-vl:8b")
    names = [m.get("model") or m.get("name") for m in ollama.list().get("models", [])]
    if not any(n and n.startswith(model.split(":")[0]) for n in names):
        raise RuntimeError(f"{model} not pulled")
    r = ollama.chat(model=model, messages=[{
        "role": "user",
        "content": "Transcribe every line of text in this image exactly, preserving line breaks. "
                   "Output only the text, no commentary.",
        "images": [path]}], options={"temperature": 0})
    return r["message"]["content"]

# ----------------------------------------------------------------------------- main

def status_for(name):
    spec = ENGINES[name]
    if spec["platforms"] and platform.system() not in spec["platforms"]:
        return "wrong OS"
    if not have(spec["needs"]):
        return "not installed"
    if name.startswith("tesseract") and not find_tesseract():
        return "tesseract.exe missing"
    return "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", help="image file (png/jpg/tif)")
    ap.add_argument("--gt", help="ground truth text file for CER/WER")
    ap.add_argument("--engines", help="comma list to run (default: all installed)")
    ap.add_argument("--save", help="directory to write <engine>.txt outputs")
    ap.add_argument("--list", action="store_true", help="list engines and install status, then exit")
    ap.add_argument("--full", action="store_true", help="print full output of each engine")
    args = ap.parse_args()

    if args.list or not args.image:
        print(f"{'engine':22} {'needs':22} status")
        for n in ENGINES:
            print(f"{n:22} {ENGINES[n]['needs']:22} {status_for(n)}")
        if not args.image:
            return
        print()

    if not os.path.exists(args.image):
        sys.exit(f"no such file: {args.image}")
    gt = open(args.gt, encoding="utf-8").read() if args.gt else None
    wanted = [e.strip() for e in args.engines.split(",")] if args.engines else list(ENGINES)
    if args.save:
        os.makedirs(args.save, exist_ok=True)

    rows = []
    for name in wanted:
        if name not in ENGINES:
            rows.append((name, "unknown engine", 0, 0, None, None, ""))
            continue
        st = status_for(name)
        if st != "ok":
            rows.append((name, st, 0, 0, None, None, ""))
            continue
        t0 = time.perf_counter()
        try:
            text = ENGINES[name]["fn"](args.image) or ""
            dt = time.perf_counter() - t0
            c = cer(gt, text) if gt else None
            w = wer(gt, text) if gt else None
            rows.append((name, "ok", dt, len(normalize(text)), c, w, text))
            if args.save:
                with open(os.path.join(args.save, f"{name}.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
        except Exception as e:  # noqa: BLE001
            dt = time.perf_counter() - t0
            rows.append((name, f"error: {type(e).__name__}: {str(e)[:60]}", dt, 0, None, None, ""))

    print(f"\nimage: {args.image}   gt: {args.gt or '-'}   gpu: {gpu_available()}\n")
    print(f"{'engine':22} {'status':34} {'sec':>7} {'chars':>6} {'CER':>7} {'WER':>7}  preview")
    print("-" * 110)
    for name, st, dt, n, c, w, text in rows:
        cs = f"{c:7.3f}" if c is not None and c == c else "      -"
        ws = f"{w:7.3f}" if w is not None and w == w else "      -"
        prev = normalize(text).replace("\n", " | ")[:60]
        print(f"{name:22} {st[:34]:34} {dt:7.2f} {n:6d} {cs} {ws}  {prev}")
    if args.full:
        for name, st, dt, n, c, w, text in rows:
            if st == "ok":
                print(f"\n===== {name} =====\n{text}")


if __name__ == "__main__":
    main()
