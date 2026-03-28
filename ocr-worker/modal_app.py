"""
Textara OCR Pipeline — Modal GPU endpoint
==========================================
Receives a PDF as raw bytes, returns a DOCX as raw bytes.

Pipeline per page:
  1. pdf2image → PIL images at 300 DPI
  2. Detectron2 layout model → bounding boxes (7 classes)
  3. Crop each region, sort Arabic-order (RTL within row, top-to-bottom)
  4. Qari OCR (Qwen2-VL 2B) on each cropped region
  5. Assemble python-docx with proper RTL styles

Deploy:  modal deploy ocr-worker/modal_app.py
Call:    textara_ocr = modal.Function.lookup("textara-ocr", "process_pdf")
         docx_bytes  = textara_ocr.remote(pdf_bytes)
"""

import io
import os
import tempfile

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "poppler-utils",
        "libgl1-mesa-glx",
        "libglib2.0-0",
        "wget",
        "git",
    )
    .pip_install(
        "numpy<2",
        "torch==2.1.2",
        "torchvision==0.16.2",
        "transformers==4.49.0",
        "qwen-vl-utils",
        "accelerate>=0.26.0",
        "bitsandbytes",
        "opencv-python-headless",
        "fvcore",
        "iopath",
        "pdf2image",
        "Pillow",
        "python-docx",
        "boto3",
    )
    .run_commands(
        "pip install 'detectron2 @ git+https://github.com/facebookresearch/detectron2.git'"
    )
)

app = modal.App("textara-ocr", image=image)

LABEL_MAP = {
    0: "page_number",
    1: "section_header",
    2: "paragraph",
    3: "title",
    4: "figure",
    5: "footer",
    6: "subtitle",
}

SKIP_LABELS = {"page_number", "footer", "figure"}

STYLE_MAP = {
    "title": ("Heading 1", True),
    "section_header": ("Heading 2", True),
    "subtitle": ("Heading 3", False),
    "paragraph": ("Normal", False),
}


@app.cls(
    gpu="A10G",
    timeout=600,
    secrets=[modal.Secret.from_name("textara-r2")],
    min_containers=0,
)
class OCRPipeline:
    @modal.enter()
    def load_models(self):
        import boto3
        import torch
        from botocore.client import Config
        from detectron2 import model_zoo
        from detectron2.config import get_cfg
        from detectron2.engine import DefaultPredictor
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        # --- Layout model (Detectron2) ---
        print("Downloading layout model from R2...")
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4"),
        )
        os.makedirs("/weights", exist_ok=True)
        s3.download_file(
            os.environ["R2_BUCKET_NAME"],
            "models/layout/model_final.pth",
            "/weights/model_final.pth",
        )
        print("Layout model downloaded.")

        cfg = get_cfg()
        cfg.merge_from_file(
            model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")
        )
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7
        cfg.MODEL.WEIGHTS = "/weights/model_final.pth"
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
        cfg.MODEL.DEVICE = "cuda"
        self.layout_predictor = DefaultPredictor(cfg)
        print("Layout model loaded.")

        # --- Qari OCR model ---
        print("Loading Qari OCR model from HuggingFace...")
        model_id = "NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct"
        self.ocr_processor = AutoProcessor.from_pretrained(
            model_id, trust_remote_code=True
        )
        self.ocr_model = (
            Qwen2VLForConditionalGeneration.from_pretrained(
                model_id,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True,
            ).eval()
        )
        print("OCR model loaded.")

    @modal.method()
    def process_pdf(self, pdf_bytes: bytes) -> bytes:
        """
        Takes raw PDF bytes, returns raw DOCX bytes.
        """
        from pdf2image import convert_from_bytes
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        import cv2
        import numpy as np

        print("Converting PDF to images...")
        pages = convert_from_bytes(pdf_bytes, dpi=300)
        print(f"  {len(pages)} pages")

        doc = Document()
        _configure_rtl_document(doc)

        for page_num, page_img in enumerate(pages):
            print(f"Processing page {page_num + 1}/{len(pages)}")

            page_cv = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
            outputs = self.layout_predictor(page_cv)
            instances = outputs["instances"].to("cpu")
            regions = _extract_regions(instances, page_img)

            if not regions:
                text = self._ocr_image(page_img)
                if text.strip():
                    _add_paragraph(doc, text, "Normal")
                continue

            for region in regions:
                label = LABEL_MAP.get(region["class_id"], "paragraph")
                if label in SKIP_LABELS:
                    continue
                cropped = page_img.crop(region["bbox"])
                text = self._ocr_image(cropped)
                if not text.strip():
                    continue
                style_name, bold = STYLE_MAP.get(label, ("Normal", False))
                _add_paragraph(doc, text, style_name, bold)

        buf = io.BytesIO()
        doc.save(buf)
        print("Done.")
        return buf.getvalue()

    def _ocr_image(self, pil_image) -> str:
        """Run Qari OCR on a PIL image, return extracted Arabic text."""
        import torch
        from qwen_vl_utils import process_vision_info

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pil_image.save(tmp.name)
            tmp_path = tmp.name

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": f"file://{tmp_path}"},
                        {
                            "type": "text",
                            "text": "Extract the plain text from this document image. No hallucination.",
                        },
                    ],
                }
            ]
            text_input = self.ocr_processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, _ = process_vision_info(messages)
            inputs = self.ocr_processor(
                text=[text_input],
                images=image_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda")

            with torch.inference_mode():
                generated_ids = self.ocr_model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False,
                    num_beams=1,
                )

            trimmed = [
                out[len(inp) :] for inp, out in zip(inputs.input_ids, generated_ids)
            ]
            return self.ocr_processor.batch_decode(
                trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )[0]
        finally:
            os.unlink(tmp_path)


def _extract_regions(instances, page_img) -> list:
    """
    Extract detected regions sorted in Arabic reading order:
    top-to-bottom rows, right-to-left within each row.
    Rows are grouped by a vertical overlap tolerance.
    """
    if len(instances) == 0:
        return []

    boxes = instances.pred_boxes.tensor.numpy()
    scores = instances.scores.numpy()
    classes = instances.pred_classes.numpy()

    regions = []
    for box, score, cls in zip(boxes, scores, classes):
        x1, y1, x2, y2 = map(int, box)
        regions.append({
            "bbox": (x1, y1, x2, y2),
            "class_id": int(cls),
            "score": float(score),
        })

    # Sort top-to-bottom by y1
    regions.sort(key=lambda r: r["bbox"][1])

    # Group into rows (overlap tolerance: 20px)
    rows = []
    for region in regions:
        placed = False
        for row in rows:
            rep = row[0]
            if region["bbox"][1] < rep["bbox"][3] + 20:
                row.append(region)
                placed = True
                break
        if not placed:
            rows.append([region])

    # Sort each row RTL (right-to-left: descending x1)
    sorted_regions = []
    for row in rows:
        row.sort(key=lambda r: -r["bbox"][0])
        sorted_regions.extend(row)

    return sorted_regions


def _configure_rtl_document(doc) -> None:
    """Set document defaults for RTL Arabic text."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt

    # Set RTL on Normal paragraph style
    pPr = doc.styles["Normal"].paragraph_format._element
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)

    # Set Arabic font for all heading/body styles
    for style_name in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[style_name]
        style.font.name = "Arial"
        rPr = style.element.get_or_add_rPr()
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:cs"), "Arial")
        rPr.append(rFonts)


def _add_paragraph(doc, text: str, style_name: str = "Normal", bold: bool = False) -> None:
    """Add an RTL paragraph to the document."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    para = doc.add_paragraph(style=style_name)
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    pPr = para._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)

    run = para.add_run(text)
    run.bold = bold
    rPr = run._r.get_or_add_rPr()
    cs = OxmlElement("w:cs")
    rPr.append(cs)
