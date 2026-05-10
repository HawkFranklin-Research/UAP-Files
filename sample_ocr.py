import fitz
import easyocr
import cv2
import numpy as np
import sys

def ocr_sample(pdf_path, num_pages=3):
    print(f"FILE: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        reader = easyocr.Reader(['en'])
        for i in range(min(num_pages, len(doc))):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            results = reader.readtext(img_array)
            print(f"--- Page {i} ---")
            for (bbox, text, prob) in results:
                print(text)
    except Exception as e:
        print(f"Error: {e}")
    print("---")

if __name__ == "__main__":
    ocr_sample("ufo_release/Department of War/PDF/38_143685_box7_Incident_Summaries_1-100.pdf")
    ocr_sample("ufo_release/Department of War/PDF/38_143685_box_Incident_Summaries_101-172.pdf")
