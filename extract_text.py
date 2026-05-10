import sys
import fitz
import easyocr
import cv2
import numpy as np

if len(sys.argv) < 2:
    print("Usage: python extract_text.py <pdf_path>")
    sys.exit(1)

doc = fitz.open(sys.argv[1])
reader = easyocr.Reader(['en'])

for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    
    results = reader.readtext(img_array)
    print(f"--- Page {i} ---")
    for (bbox, text, prob) in results:
        print(text)
