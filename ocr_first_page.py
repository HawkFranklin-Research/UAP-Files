import fitz
import easyocr
import numpy as np
import cv2
import sys

def ocr_first_page(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        reader = easyocr.Reader(['en'])
        results = reader.readtext(img_array)
        text = " ".join([res[1] for res in results])
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(f"FILE: {path}")
        print(ocr_first_page(path))
        print("---")
