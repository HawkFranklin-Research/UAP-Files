import fitz
import sys

def extract_partial_text(pdf_path, max_pages=10):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for i in range(min(max_pages, len(doc))):
            page = doc.load_page(i)
            text += f"--- Page {i} ---\n"
            text += page.get_text()
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(f"FILE: {path}")
        print(extract_partial_text(path))
        print("---")
