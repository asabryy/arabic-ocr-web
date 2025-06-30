from pdf2image import convert_from_bytes

def convert_pdf_to_images(pdf_path, dpi=200):
    with open(pdf_path, "rb") as f:
        return convert_from_bytes(f.read(), dpi=dpi)