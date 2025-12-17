from io import BytesIO
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from PIL import Image
import csv
import pytesseract

def parse_file_from_bytes(file_bytes: bytes, file_name: str) -> str:
    """
    Universal file parser that extracts text from PDF, DOCX, XLSX, CSV, PPTX, TXT, and images.
    """
    ext = file_name.lower().split(".")[-1]
    
    print("DEBUG FILE NAME RECEIVED:", file_name)

    # PDF

    if ext == "pdf":
        reader = PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    # DOCX
 
    elif ext == "docx":
        doc = Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    # TXT

    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")

    # XLSX

    elif ext == "xlsx":
        wb = load_workbook(BytesIO(file_bytes), data_only=True)
        text = ""
        for sheet in wb:
            for row in sheet.iter_rows(values_only=True):
                row_text = " ".join([str(cell) if cell is not None else "" for cell in row])
                text += row_text + "\n"
        return text

    # CSV
 
    elif ext == "csv":
        text = ""
        f = BytesIO(file_bytes).read().decode("utf-8", errors="ignore").splitlines()
        reader = csv.reader(f)
        for row in reader:
            text += " ".join(row) + "\n"
        return text

    # PPTX
  
    elif ext == "pptx":
        prs = Presentation(BytesIO(file_bytes))
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text

    # Image OCR (PNG, JPG)

    elif ext in ["png", "jpg", "jpeg"]:
        try:
            image = Image.open(BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            return f"[IMAGE FILE: OCR FAILED or DISABLED]"

    # Unsupported formats

    else:
        return f"[Unsupported file format: {ext}]"
