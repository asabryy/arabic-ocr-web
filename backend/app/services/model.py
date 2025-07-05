import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

model_name = "NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct"

model = Qwen2VLForConditionalGeneration.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

processor = AutoProcessor.from_pretrained(model_name, use_fast=True)