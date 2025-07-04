import layoutparser as lp
from pdf2image import convert_from_path
import cv2
import numpy as np

# --- Convert PDF to images ---
pdf_path = "sample.pdf"
pages = convert_from_path(pdf_path, dpi=300)  # You can loop through multiple pages

# --- Convert PIL image to OpenCV format ---
image = np.array(pages[0])
image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

# --- Load PubLayNet model for layout detection ---
model = lp.Detectron2LayoutModel(
    config_path='lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
    extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5],
    label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
)

# --- Detect layout blocks ---
layout = model.detect(image)

# --- Visualize results (optional) ---
lp.draw_box(image, layout, box_width=3).show()

# --- Output block data ---
for block in layout:
    print(f"Type: {block.type}, Coordinates: {block.block.x_1, block.block.y_1, block.block.x_2, block.block.y_2}")
