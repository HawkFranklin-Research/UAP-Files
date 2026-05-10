import fitz
import sys

def extract_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(f"FILE: {path}")
        print(extract_text(path))
        print("---")
