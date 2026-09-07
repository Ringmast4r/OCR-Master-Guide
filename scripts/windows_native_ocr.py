#!/usr/bin/env python3
"""windows_native_ocr.py: use the OCR engines that ship inside Windows from Python.

    python scripts/windows_native_ocr.py samples/screenshot_ui.png
    python scripts/windows_native_ocr.py shot.png --engine winocr --lang en --json
    python scripts/windows_native_ocr.py shot.png --engine oneocr

Engines:
  oneocr  - the Snipping Tool engine (Windows 11; works on 10 with the 3 files copied).
            pip install oneocr, then follow https://github.com/AuroraWright/oneocr to place
            oneocr.dll, oneocr.onemodel, onnxruntime.dll next to this script or in %USERPROFILE%\\.config\\oneocr
  winocr  - Windows.Media.Ocr (Windows 10+). pip install winocr. Needs the OCR language capability:
            Settings > Language > (language) > Options > Optical character recognition
Default: try oneocr, fall back to winocr.
"""
import argparse
import json
import platform
import sys


def run_oneocr(path):
    import oneocr
    from PIL import Image
    eng = oneocr.OcrEngine()
    r = eng.recognize_pil(Image.open(path).convert("RGB"))
    lines = []
    for ln in r.get("lines", []):
        lines.append({"text": ln.get("text", ""),
                      "bbox": ln.get("bounding_rect"),
                      "words": [{"text": w.get("text"), "conf": w.get("confidence"), "bbox": w.get("bounding_rect")}
                                for w in ln.get("words", [])]})
    return {"engine": "oneocr", "text": r.get("text", ""), "angle": r.get("text_angle"), "lines": lines}


def run_winocr(path, lang):
    import winocr
    from PIL import Image
    r = winocr.recognize_pil_sync(Image.open(path).convert("RGB"), lang)
    lines = []
    for ln in r.get("lines", []):
        lines.append({"text": ln.get("text", ""),
                      "words": [{"text": w.get("text"), "bbox": w.get("bounding_rect")} for w in ln.get("words", [])]})
    return {"engine": "winocr", "text": r.get("text", ""), "angle": r.get("text_angle"), "lines": lines}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--engine", choices=["auto", "oneocr", "winocr"], default="auto")
    ap.add_argument("--lang", default="en", help="winocr language tag (en, de, fr, ja, zh-Hans ...)")
    ap.add_argument("--json", action="store_true", help="print full JSON with boxes and confidences")
    args = ap.parse_args()

    if platform.system() != "Windows":
        sys.exit("Windows only. On Linux use NormCap, RapidOCR, or Tesseract (see docs/05-linux-stack.md).")

    errors = []
    order = ["oneocr", "winocr"] if args.engine == "auto" else [args.engine]
    result = None
    for eng in order:
        try:
            result = run_oneocr(args.image) if eng == "oneocr" else run_winocr(args.image, args.lang)
            break
        except ImportError as e:
            errors.append(f"{eng}: not installed ({e}); pip install {eng}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{eng}: {type(e).__name__}: {e}")
    if result is None:
        sys.exit("no engine worked:\n  " + "\n  ".join(errors))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"[{result['engine']}] angle={result.get('angle')}")
        print(result["text"])
    if errors:
        print("\nnotes:\n  " + "\n  ".join(errors), file=sys.stderr)


if __name__ == "__main__":
    main()
