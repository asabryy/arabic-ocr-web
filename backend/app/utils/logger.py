import logging

logger = logging.getLogger("arabic-ocr")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():  # Prevent duplicate handlers if already configured
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
