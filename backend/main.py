from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from PIL import Image
import torch, os, uuid, gc
from docx import Document
from qwen_vl_utils import process_vision_info

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_name = "NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct"
model = Qwen2VLForConditionalGeneration.from_pretrained(
    model_name, torch_dtype=torch.float16
).to("cuda")
processor = AutoProcessor.from_pretrained(model_name)

@app.post("/upload")
async def upload_pdf(file: UploadFile):
    input_path = f"uploads/{uuid.uuid4().hex}.pdf"
    os.makedirs("uploads", exist_ok=True)
    with open(input_path, "wb") as f:
        f.write(await file.read())

    images = convert_from_path(input_path, dpi=300)
    doc = Document()

    for i, image in enumerate(images):
        prompt = (
            "Extract all Arabic text exactly as it appears in the image, including all diacritical marks (tashkeel), "
            "line breaks, paragraphs, and structure. Do not summarize. Do not skip any line."
        )
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt}
        ]}]
        text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        with torch.no_grad():
            image_inputs, _ = process_vision_info(messages)
            inputs = processor(text=[text_prompt], images=image_inputs, return_tensors="pt", padding=True).to(model.device)
            output = model.generate(**inputs, max_new_tokens=1500, temperature=0.7, top_p=0.95, do_sample=True)
            generated_tokens = output[:, inputs["input_ids"].shape[-1]:]
            result = processor.batch_decode(generated_tokens, skip_special_tokens=True)[0]

        doc.add_heading(f"Page {i+1}", level=2)
        for para in result.strip().split("\n\n"):
            doc.add_paragraph(para.strip())

        del inputs, output, image_inputs
        torch.cuda.empty_cache()
        gc.collect()

    out_path = f"{input_path}.docx"
    doc.save(out_path)
    return FileResponse(out_path, filename="arabic_ocr_output.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
