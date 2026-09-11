import fitz  # PyMuPDF
from fastapi import HTTPException, status


def count_pages(pdf_bytes: bytes) -> int:
    """Number of pages in a PDF, validating it is a readable, unencrypted PDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF")
    try:
        if doc.needs_pass:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encrypted PDFs are not supported",
            )
        n = len(doc)
    finally:
        doc.close()
    if n < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF has no pages")
    return n
