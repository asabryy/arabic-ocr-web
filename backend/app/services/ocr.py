from app.services.pdf_utils import convert_pdf_to_images
from app.services.docx_writer import save_docx
from app.core.config import UPLOAD_DIR, OUTPUT_DIR
from app.utils.logger import logger
import os
from datetime import datetime
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

model_name = "NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct"
model = Qwen2VLForConditionalGeneration.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
processor = AutoProcessor.from_pretrained(model_name)
prompt = "Extract the Arabic text from the image below. while maintaing layout and structure of the paragraphs and headings for docx file format"


def ocr_page(image, page_number=None):
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
    prompt_text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, _ = process_vision_info(messages)
    inputs = processor(text=[prompt_text], images=image_inputs, return_tensors="pt", padding=True).to(model.device)
    output = model.generate(**inputs, max_new_tokens=2000)
    generated_tokens = output[:, inputs["input_ids"].shape[-1]:]
    decoded = processor.batch_decode(generated_tokens, skip_special_tokens=True)[0].strip()

    if page_number is not None:
        logger.info(f"[DEBUG] Page {page_number}:")
        logger.info(f"Prompt Length: {len(prompt_text)}")
        logger.info(f"Generated Token Count: {len(generated_tokens[0])}")
        logger.info(f"OCR Output:\n{decoded}\n")

    return decoded


async def run_ocr_pipeline(file):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name = os.path.splitext(file.filename)[0].replace(" ", "_")
    safe_name = f"{name}_{timestamp}"
    pdf_path = os.path.join(UPLOAD_DIR, f"{safe_name}.pdf")
    output_path = os.path.join(OUTPUT_DIR, f"{safe_name}.docx")

    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    images = convert_pdf_to_images(pdf_path)
    logger.info(f"Converting {len(images)} pages to text")

    texts = []
    for i, img in enumerate(images, start=1):
        text = ocr_page(img, page_number=i)
        texts.append(text)

    save_docx(texts, output_path)
    return os.path.basename(output_path)
