#!/usr/bin/env python3
"""tesseract_quickstart.py: zero-dependency Tesseract sanity check and PSM sweep.

    python scripts/tesseract_quickstart.py samples/clean_300dpi.png
    python scripts/tesseract_quickstart.py page.png --lang eng --psm 3,4,6,11 --save out/

Finds tesseract.exe (PATH or the UB Mannheim default folder), prints version and languages,
runs each PSM, reports characters found and mean word confidence from the TSV output,
and writes the best PSM's text/tsv/hocr if --save is given. Stdlib only.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys


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


def run(exe, args, timeout=120):
    p = subprocess.run([exe] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def tsv_stats(tsv):
    confs, words = [], 0
    for line in tsv.splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 12:
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        txt = cols[11].strip()
        if conf >= 0 and txt:
            confs.append(conf)
            words += 1
    return (sum(confs) / len(confs) if confs else 0.0), words


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--lang", default="eng")
    ap.add_argument("--psm", default="3,4,6,11", help="comma list of PSMs to try")
    ap.add_argument("--oem", default="1")
    ap.add_argument("--dpi", default=None, help="pass --dpi to tesseract (e.g. 300 for screenshots you upscaled)")
    ap.add_argument("--extra", default="", help='extra args, e.g. "-c preserve_interword_spaces=1"')
    ap.add_argument("--save", help="dir to write best.txt / best.tsv / best.hocr")
    args = ap.parse_args()

    exe = find_tesseract()
    if not exe:
        sys.exit("tesseract not found. Windows: winget install UB-Mannheim.TesseractOCR. Linux: apt install tesseract-ocr")
    print(f"tesseract: {exe}")
    rc, out, err = run(exe, ["--version"])
    print((out or err).splitlines()[0])
    rc, out, err = run(exe, ["--list-langs"])
    langs = [l.strip() for l in (out or err).splitlines()[1:] if l.strip()]
    print(f"languages ({len(langs)}): {', '.join(langs[:20])}{' ...' if len(langs) > 20 else ''}")
    if args.lang.split("+")[0] not in langs:
        print(f"warning: '{args.lang}' not in installed languages; download from tessdata_best into TESSDATA_PREFIX")
    print(f"TESSDATA_PREFIX={os.environ.get('TESSDATA_PREFIX', '(unset)')}\n")

    base = ["-l", args.lang, "--oem", args.oem]
    if args.dpi:
        base += ["--dpi", str(args.dpi)]
    base += args.extra.split()

    print(f"{'psm':>4} {'words':>6} {'chars':>6} {'meanconf':>9}  preview")
    print("-" * 80)
    best = None
    results = {}
    for psm in [p.strip() for p in args.psm.split(",") if p.strip()]:
        rc, txt, err = run(exe, [args.image, "stdout", "--psm", psm] + base)
        rc2, tsv, err2 = run(exe, [args.image, "stdout", "--psm", psm] + base + ["tsv"])
        if rc != 0:
            print(f"{psm:>4}  error: {err.strip()[:70]}")
            continue
        conf, words = tsv_stats(tsv)
        chars = len(txt.strip())
        results[psm] = (txt, tsv)
        prev = " ".join(txt.split())[:50]
        print(f"{psm:>4} {words:6d} {chars:6d} {conf:9.1f}  {prev}")
        score = words * conf
        if best is None or score > best[0]:
            best = (score, psm)

    if best and args.save:
        os.makedirs(args.save, exist_ok=True)
        psm = best[1]
        txt, tsv = results[psm]
        open(os.path.join(args.save, "best.txt"), "w", encoding="utf-8").write(txt)
        open(os.path.join(args.save, "best.tsv"), "w", encoding="utf-8").write(tsv)
        rc, hocr, err = run(exe, [args.image, "stdout", "--psm", psm] + base + ["hocr"])
        open(os.path.join(args.save, "best.hocr"), "w", encoding="utf-8").write(hocr)
        print(f"\nbest psm {psm} -> {args.save}/best.txt, best.tsv, best.hocr")
    elif best:
        print(f"\nbest psm by words x confidence: {best[1]}")


if __name__ == "__main__":
    main()
