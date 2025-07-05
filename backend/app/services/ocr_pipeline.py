import os
from datetime import datetime
from app.services.pdf_utils import convert_pdf_to_images
from app.services.inference import ocr_page
from app.services.html_utils import write_html_to_docx
from app.utils.logger import logger
from app.utils.benchmark_utils import Timer, log_system_usage
from app.core.config import UPLOAD_DIR, OUTPUT_DIR

async def run_ocr_pipeline(file) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name = os.path.splitext(file.filename)[0].replace(" ", "_")
    safe_name = f"{name}_{timestamp}"
    pdf_path = os.path.join(UPLOAD_DIR, f"{safe_name}.pdf")
    output_path = os.path.join(OUTPUT_DIR, f"{safe_name}.docx")

    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    images = convert_pdf_to_images(pdf_path)
    logger.info(f"Converting {len(images)} pages to HTML text")

    html_content = ""
    with Timer("Full OCR Pipeline", logger):
        for i, img in enumerate(images, start=1):
            with Timer(f"OCR Page {i}", logger):
                html = ocr_page(img, page_number=i)
                html_content += html + "\n"
                log_system_usage(logger)
                
    write_html_to_docx(html_content, output_path)
    return os.path.basename(output_path)
