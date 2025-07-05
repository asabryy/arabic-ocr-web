import torch
from app.services.model import model, processor
from qwen_vl_utils import process_vision_info
from app.utils.logger import logger

prompt = (
    "Extract all Arabic text from the image accurately. Do not skip any words or remove spaces. "
    "Preserve correct spelling, Arabic diacritics, and natural reading order. "
    "Do not convert paragraph indentation into headers or change formatting unexpectedly."
)

@torch.inference_mode()
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
        logger.info(f"OCR Output:\n{decoded[:250]}\n")

    return decoded
