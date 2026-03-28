"""
PDF Text Extraction Service for Smart Accounting.
Responsible for reading raw text from PDF files to be processed 
by the tax information extraction engine.
"""

import pdfplumber

class PdfTextExtractionService:
    def extract_text(self, file_path: str) -> str:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text(layout=True) + "\n"
        return text