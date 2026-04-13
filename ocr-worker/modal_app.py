"""
Textara OCR Pipeline — Modal GPU endpoint
==========================================
Production wrapper around pipeline.py for Modal.com.

Receives a PDF as raw bytes, returns a DOCX as raw bytes.
All OCR logic lives in pipeline.py — edit that file, not this one.

Deploy:  modal deploy ocr-worker/modal_app.py
Call:    OCRPipeline = modal.Cls.from_name("textara-ocr", "OCRPipeline")
         docx_bytes  = OCRPipeline().process_pdf.remote(pdf_bytes)
"""

import io

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libmupdf-dev",
        "mupdf-tools",
    )
    .pip_install(
        "numpy<2",
        "torch==2.4.0",
        "torchvision==0.19.0",
        "transformers>=4.49.0",
        "qwen-vl-utils",
        "accelerate>=0.26.0",
        "peft",
        "pymupdf",
        "Pillow",
        "python-docx",
    )
)

app = modal.App("textara-ocr", image=image)

pipeline_mount = modal.Mount.from_local_file(
    local_path="ocr-worker/pipeline.py",
    remote_path="/root/pipeline.py",
)


@app.cls(
    gpu="A10G",
    timeout=600,
    min_containers=0,
    mounts=[pipeline_mount],
)
class OCRPipeline:
    @modal.enter()
    def load_models(self):
        from pipeline import load_model
        self.model, self.processor, _ = load_model()

    @modal.method()
    def process_pdf(self, pdf_bytes: bytes) -> bytes:
        """Takes raw PDF bytes, returns raw DOCX bytes."""
        import fitz
        from pipeline import render_page, ocr_page, build_docx

        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n_pages = len(pdf_doc)
        print(f"PDF: {n_pages} page(s)")

        pages_text = []
        for i, page in enumerate(pdf_doc, 1):
            print(f"  Page {i}/{n_pages} — rendering...")
            img = render_page(page)
            print(f"  Page {i}/{n_pages} — OCR ({img.width}x{img.height}px)...")
            text, elapsed, _ = ocr_page(img, self.model, self.processor)
            print(f"  Page {i}/{n_pages} — {len(text)} chars in {elapsed:.1f}s")
            pages_text.append(text)

        pdf_doc.close()

        buf = io.BytesIO()
        build_docx(pages_text, buf)
        print("Done.")
        return buf.getvalue()
