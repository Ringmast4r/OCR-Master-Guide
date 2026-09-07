#!/usr/bin/env python3
"""preprocess.py: OpenCV cleanup for classical OCR engines (Tesseract, Kraken, OCRmyPDF).

    python scripts/preprocess.py photo.jpg -o clean.png --perspective --deskew --binarize sauvola --denoise --upscale auto --trim
    python scripts/preprocess.py scan.png  -o clean.png --deskew --binarize adaptive --show

Do NOT feed the binarized output to PaddleOCR/RapidOCR/VLMs; give them the color original
(at most --perspective and --deskew). See docs/08-preprocessing.md.
"""
import argparse
import sys

import cv2
import numpy as np


def find_page_quad(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(g, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = img.shape[0] * img.shape[1]
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.2 * area:
            pts = approx.reshape(4, 2).astype(np.float32)
            s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
            return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)
    return None


def four_point(img, pts):
    tl, tr, br, bl = pts
    W = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    H = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(pts, dst), (W, H))


def estimate_xheight(gray):
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    hs = [int(h) for x, y, w, h, a in stats[1:] if 4 < h < gray.shape[0] // 10 and a > 10]
    return float(np.median(hs)) if hs else 0.0


def upscale(gray, factor, target_xheight=24.0):
    if factor == "auto":
        xh = estimate_xheight(gray)
        if xh <= 0:
            return gray, 1.0
        f = max(1.0, min(target_xheight / xh, 4.0))
    else:
        f = float(factor)
    if abs(f - 1.0) < 0.05:
        return gray, 1.0
    return cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC), f


def remove_background(gray, kernel=51):
    bg = cv2.medianBlur(gray, kernel | 1)
    return cv2.divide(gray, bg, scale=255)


def deskew_angle_rect(gray):
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(bw > 0))
    if len(coords) < 100:
        return 0.0
    angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    if angle < -45:
        angle += 90
    if angle > 45:
        angle -= 90
    return float(angle)


def deskew_angle_hough(gray):
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=150,
                            minLineLength=max(50, gray.shape[1] // 4), maxLineGap=20)
    if lines is None:
        return 0.0
    angs = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in lines[:, 0]]
    angs = [a for a in angs if abs(a) < 15]
    return float(np.median(angs)) if angs else 0.0


def deskew_angle_projection(gray):
    """Rotate through candidate angles, pick the one with the sharpest horizontal projection profile."""
    small = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA) if max(gray.shape) > 1500 else gray
    bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    best, best_score = 0.0, -1.0
    for a in np.arange(-6.0, 6.01, 0.25):
        r = rotate(bw, a, border=0)
        prof = r.sum(axis=1).astype(np.float64)
        score = float(np.var(np.diff(prof)))
        if score > best_score:
            best, best_score = float(a), score
    return best


def rotate(img, angle, border=255):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def binarize(gray, method, block=31, C=15, window=25, k=0.2):
    if method == "none":
        return gray
    if method == "otsu":
        return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    if method == "adaptive":
        return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block | 1, C)
    if method == "sauvola":
        try:
            from skimage.filters import threshold_sauvola
        except ImportError:
            print("scikit-image not installed; falling back to adaptive", file=sys.stderr)
            return binarize(gray, "adaptive", block, C)
        t = threshold_sauvola(gray, window_size=window | 1, k=k)
        return ((gray > t) * 255).astype(np.uint8)
    raise ValueError(method)


def trim_borders(bw, margin=10):
    coords = cv2.findNonZero(255 - bw)
    if coords is None:
        return bw
    x, y, w, h = cv2.boundingRect(coords)
    return bw[max(y - margin, 0):y + h + margin, max(x - margin, 0):x + w + margin]


def kill_black_edges(bw):
    h, w = bw.shape
    while h > 10 and (bw[0] < 128).mean() > 0.9:
        bw, h = bw[1:], h - 1
    while h > 10 and (bw[-1] < 128).mean() > 0.9:
        bw, h = bw[:-1], h - 1
    while w > 10 and (bw[:, 0] < 128).mean() > 0.9:
        bw, w = bw[:, 1:], w - 1
    while w > 10 and (bw[:, -1] < 128).mean() > 0.9:
        bw, w = bw[:, :-1], w - 1
    return bw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None, help="default: <input>_clean.png")
    ap.add_argument("--perspective", action="store_true", help="find the page quad and warp it flat")
    ap.add_argument("--upscale", default=None, help="factor (e.g. 2) or 'auto' (target x-height 24 px)")
    ap.add_argument("--denoise", action="store_true", help="fastNlMeansDenoising h=10")
    ap.add_argument("--background", action="store_true", help="flatten uneven illumination")
    ap.add_argument("--deskew", nargs="?", const="rect", choices=["rect", "hough", "projection"],
                    help="deskew method (default rect)")
    ap.add_argument("--binarize", default="none", choices=["none", "otsu", "adaptive", "sauvola"])
    ap.add_argument("--block", type=int, default=31, help="adaptive block size")
    ap.add_argument("--C", type=int, default=15, help="adaptive constant")
    ap.add_argument("--window", type=int, default=25, help="sauvola window")
    ap.add_argument("--k", type=float, default=0.2, help="sauvola k")
    ap.add_argument("--close", action="store_true", help="morphological close 2x2 (join broken strokes)")
    ap.add_argument("--open", action="store_true", help="morphological open 2x2 (remove specks)")
    ap.add_argument("--edges", action="store_true", help="drop black scanner bands at the borders")
    ap.add_argument("--trim", action="store_true", help="crop to ink bounding box + margin")
    ap.add_argument("--invert", action="store_true", help="invert (dark-mode screenshots)")
    ap.add_argument("--show", action="store_true", help="also write <output>_preview.png side by side")
    args = ap.parse_args()

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read {args.input}")
    log = []

    if args.perspective:
        quad = find_page_quad(img)
        if quad is not None:
            img = four_point(img, quad)
            log.append("perspective: warped")
        else:
            log.append("perspective: no quad found, skipped")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if args.invert:
        gray = 255 - gray
        log.append("invert")
    if args.upscale:
        gray, f = upscale(gray, args.upscale)
        log.append(f"upscale x{f:.2f}")
    if args.background:
        gray = remove_background(gray)
        log.append("background flattened")
    if args.denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        log.append("denoised")
    if args.deskew:
        fn = {"rect": deskew_angle_rect, "hough": deskew_angle_hough, "projection": deskew_angle_projection}[args.deskew]
        ang = fn(gray)
        if abs(ang) > 0.1:
            gray = rotate(gray, ang)
        log.append(f"deskew({args.deskew}) {ang:+.2f} deg")

    out = binarize(gray, args.binarize, args.block, args.C, args.window, args.k)
    if args.binarize != "none":
        log.append(f"binarize {args.binarize}")
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        if args.close:
            out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, k); log.append("close")
        if args.open:
            out = cv2.morphologyEx(out, cv2.MORPH_OPEN, k); log.append("open")
        if args.edges:
            out = kill_black_edges(out); log.append("edges")
        if args.trim:
            out = trim_borders(out); log.append("trim")

    output = args.output or (args.input.rsplit(".", 1)[0] + "_clean.png")
    cv2.imwrite(output, out)
    print(f"{args.input} -> {output}  [{'; '.join(log) or 'no-op'}]  {out.shape[1]}x{out.shape[0]}")

    if args.show:
        a = cv2.cvtColor(cv2.imread(args.input, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR)
        b = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR) if out.ndim == 2 else out
        h = max(a.shape[0], b.shape[0])
        a = cv2.resize(a, (int(a.shape[1] * h / a.shape[0]), h))
        b = cv2.resize(b, (int(b.shape[1] * h / b.shape[0]), h))
        prev = output.rsplit(".", 1)[0] + "_preview.png"
        cv2.imwrite(prev, np.hstack([a, np.full((h, 8, 3), (166, 184, 20), np.uint8), b]))
        print(f"preview -> {prev}")


if __name__ == "__main__":
    main()
