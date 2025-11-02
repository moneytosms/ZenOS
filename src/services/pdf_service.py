"""PDF text extraction service"""

import PyPDF2
import pdfplumber
from typing import Optional
import io


def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract text from PDF file
    
    Args:
        pdf_file: File-like object or bytes
        
    Returns:
        Extracted text as string
    """
    text = ""
    
    # Try pdfplumber first (better for complex PDFs)
    try:
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)  # Reset file pointer
            pdf = pdfplumber.open(pdf_file)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            pdf.close()
            if text.strip():
                return text.strip()
    except Exception:
        pass
    
    # Fallback to PyPDF2
    try:
        if hasattr(pdf_file, 'read'):
            pdf_file.seek(0)
        else:
            pdf_file = io.BytesIO(pdf_file)
        
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

