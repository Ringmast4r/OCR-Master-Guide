# 08. Preprocessing

[Back to README](../README.md) | Prev: [VLM document parsers](07-vlm-document-parsers.md) | Next: [Evaluation](09-evaluation.md)

For Tesseract and other classical engines, preprocessing is where the accuracy lives. For deep detectors it
is optional. For VLMs it is mostly harmful. This guide gives the OpenCV building blocks, the order to apply
them, and the rule for when to stop. All of it is packaged as [`scripts/preprocess.py`](../scripts/preprocess.py).

---

## The rule

| Engine class | Do | Do not |
|:-------------|:---|:-------|
| Tesseract, Kraken, Calamari, OCRmyPDF | Rasterize at 300 DPI, grayscale, deskew, binarize (Sauvola/adaptive), denoise, trim borders, upscale small text | Blur, JPEG re-save, over-erode strokes |
| PaddleOCR, RapidOCR, EasyOCR, docTR | Perspective-correct, deskew if past 5 degrees, resize so text is 20+ px | Binarize (they are trained on color), invert |
| VLMs | Perspective-correct, crop to the page, resize long side to 1024 to 1600 px | Binarize, sharpen, upscale beyond the encoder's native grid |

---

## Order of operations (classical)

```
load -> (perspective) -> grayscale -> (upscale to 300 DPI) -> denoise -> deskew -> binarize -> (morphology) -> border trim -> OCR
```

Deskew before binarize when using a Hough-based angle estimate on the grayscale gradient; deskew after
binarize when using `minAreaRect` on the ink mask. Either works; do not deskew twice.

---

## Building blocks (OpenCV, Python)

```python
import cv2, numpy as np

def load_gray(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def upscale_to_xheight(gray, target_xheight=24):
    # crude estimate: median height of connected components that look like letters
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    hs = [h for x, y, w, h, a in stats[1:] if 4 < h < gray.shape[0] // 10 and a > 10]
    if not hs: return gray
    scale = target_xheight / float(np.median(hs))
    scale = max(1.0, min(scale, 4.0))
    if scale == 1.0: return gray
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

def denoise(gray):
    return cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

def deskew_angle(gray):
    # ink mask -> minAreaRect on all ink pixels -> angle in (-45, 45]
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(bw > 0))
    if len(coords) < 100: return 0.0
    angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    if angle < -45: angle += 90
    if angle > 45: angle -= 90
    return float(angle)

def deskew_angle_hough(gray):
    # more robust on sparse pages: vote over long near-horizontal lines
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=200, minLineLength=gray.shape[1] // 4, maxLineGap=20)
    if lines is None: return 0.0
    angs = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in lines[:, 0]]
    angs = [a for a in angs if abs(a) < 15]
    return float(np.median(angs)) if angs else 0.0

def rotate(img, angle, border=255):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border)

def binarize_otsu(gray):
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

def binarize_adaptive(gray, block=31, C=15):
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block | 1, C)

def binarize_sauvola(gray, window=25, k=0.2):
    from skimage.filters import threshold_sauvola
    t = threshold_sauvola(gray, window_size=window | 1, k=k)
    return ((gray > t) * 255).astype(np.uint8)

def remove_background(gray, kernel=51):
    # divide by a heavy blur to flatten uneven illumination (shadows, scanner gradients)
    bg = cv2.medianBlur(gray, kernel | 1)
    norm = cv2.divide(gray, bg, scale=255)
    return norm

def trim_borders(bw, margin=10):
    inv = 255 - bw
    coords = cv2.findNonZero(inv)
    if coords is None: return bw
    x, y, w, h = cv2.boundingRect(coords)
    x0, y0 = max(x - margin, 0), max(y - margin, 0)
    return bw[y0:y + h + margin, x0:x + w + margin]

def kill_black_edges(bw, frac=0.02):
    # scanner edge bands: drop any fully-black rows/cols hugging the border
    h, w = bw.shape
    while h > 10 and (bw[0] < 128).mean() > 0.9: bw = bw[1:]; h -= 1
    while h > 10 and (bw[-1] < 128).mean() > 0.9: bw = bw[:-1]; h -= 1
    while w > 10 and (bw[:, 0] < 128).mean() > 0.9: bw = bw[:, 1:]; w -= 1
    while w > 10 and (bw[:, -1] < 128).mean() > 0.9: bw = bw[:, :-1]; w -= 1
    return bw

def four_point(img, pts):
    # pts: 4x2 float array of page corners (tl, tr, br, bl)
    (tl, tr, br, bl) = pts
    W = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    H = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(pts.astype(np.float32), dst)
    return cv2.warpPerspective(img, M, (W, H))

def find_page_quad(img):
    # DocScanner-style: biggest 4-point contour
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(g, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.2 * img.shape[0] * img.shape[1]:
            pts = approx.reshape(4, 2).astype(np.float32)
            s = pts.sum(axis=1); d = np.diff(pts, axis=1).ravel()
            return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])
    return None
```

Morphology when strokes are broken or bleeding:

```python
k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, k)   # join broken strokes (thin fonts, faxes)
bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k)    # remove specks
# thick/bleeding ink: erode the INK (which is black), i.e. dilate the white
bw = cv2.dilate(bw, k, iterations=1)
```

---

## Choosing a binarizer

| Method | Best on | Fails on | Parameters |
|:-------|:--------|:---------|:-----------|
| Otsu (global) | Flat, well-lit scans | Shadows, gradients, colored paper | none |
| Adaptive Gaussian (OpenCV) | Phone photos, uneven light | Very large fonts (hollow letters if block too small) | `block` ~ 2 to 3x stroke height, `C` 10 to 20 |
| Sauvola (scikit-image) | Degraded documents, historical, faxes | Slow on huge images; needs `window` tuned | `window` 15 to 51, `k` 0.2 to 0.5 |
| Niblack | Similar to Sauvola, noisier | Blank regions become noise | same |
| Background division + Otsu | Scanner gradients | Colored ink same tone as paper | kernel 51 to 101 |
| Leptonica's inside Tesseract | Anything if you set `thresholding_method=2` (Sauvola) | You cannot see it unless `tessedit_write_images=1` | `thresholding_window_size`, `thresholding_kfactor` |

Look at the result. Letters should be solid black with clean edges and no salt-and-pepper. Dump Tesseract's
own view with `-c tessedit_write_images=1` and compare.

---

## DPI arithmetic

| Source | Native | Text height | Action |
|:-------|:-------|:------------|:-------|
| Scanner at 300 DPI | 300 | 11 pt ~ 46 px cap height, ~25 px x-height | none |
| Scanner at 200 DPI | 200 | ~17 px x-height | 1.5x upscale |
| Fax | 200x100 | squashed | resize to square pixels first, then 1.5x |
| Screenshot | 96 | 8 to 12 px | 2.5x to 3x |
| 12 MP phone photo of A4 | ~350 to 400 effective | fine | downscale to 300 for speed |
| Thumbnail | <100 | <8 px | unusable; find the original |

Set `--dpi 300` or `user_defined_dpi=300` after resizing so Tesseract's internal heuristics agree with reality.

---

## Command-line equivalents

```bash
# ImageMagick
magick in.jpg -colorspace Gray -resize 200% -deskew 40% +repage -lat 25x25+10% -morphology Close Square:1 out.png
# textcleaner (Fred Weinhaus script) for phone photos
textcleaner -g -e stretch -f 25 -o 10 -u -s 1 -T -p 10 in.jpg out.png

# unpaper (Linux/WSL): deskew, despeckle, borders, black edges
unpaper --deskew-scan-direction left,right --no-grayfilter in.pgm out.pgm
# OCRmyPDF does it for you
ocrmypdf --deskew --clean --remove-background --oversample 300 in.pdf out.pdf
```

---

## The repo script

```bash
python scripts/preprocess.py photo.jpg -o clean.png --perspective --deskew --binarize sauvola --denoise --upscale auto --trim
python scripts/preprocess.py scan.png -o clean.png --deskew --binarize adaptive --show   # writes clean.png and a side-by-side preview
```

Options: `--perspective` (find page quad, warp), `--upscale N|auto`, `--denoise`, `--background` (flatten
illumination), `--deskew [hough|rect]`, `--binarize otsu|adaptive|sauvola|none`, `--close`, `--open`, `--trim`,
`--edges` (kill scanner bands), `--invert`, `--show`.

---

## When to stop

If Tesseract on the preprocessed image is still under about 95 percent character accuracy on printed text, the
problem is not preprocessing. Switch engines (RapidOCR/PaddleOCR on the original color image) and compare with
[`scripts/ocr_bench.py`](../scripts/ocr_bench.py). Preprocessing chases the last few points; engine choice moves
tens of points.
