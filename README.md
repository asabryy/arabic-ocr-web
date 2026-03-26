# Textara — Arabic OCR Web App

Converts Arabic PDFs into editable Word documents using the [Qari OCR](https://huggingface.co/NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct) model (Qwen2-VL fine-tuned for Arabic).

---

## What it does

Upload an Arabic PDF → Textara runs it through a vision-language OCR model → download a formatted, editable Word document with proper RTL layout.

---

## Architecture

| Service | Stack | Runs on |
|---------|-------|---------|
| `frontend` | React 18 + Vite + Tailwind, Arabic/English i18n | k3s |
| `auth-service` | FastAPI, SQLAlchemy, Supabase PostgreSQL, JWT | k3s |
| `doc-manager` | FastAPI, Cloudflare R2, RabbitMQ producer | k3s |
| `doc-worker` | RabbitMQ consumer (same image as doc-manager) | k3s |
| `ocr-worker` | Qari model (Qwen2-VL 2B, bf16 LoRA merge) | Modal.com A10G GPU |
| `rabbitmq` | Message broker for OCR task queue | k3s StatefulSet |

All traffic routes through an Nginx ingress on a k3s cluster hosted on Oracle Cloud Free Tier:
- `/api/auth/` → `auth-service`
- `/api/doc-manager/` → `doc-manager`
- `/` → `frontend`

The OCR pipeline runs serverlessly on Modal.com — PDFs are sent as bytes, processed page-by-page through the Qari model, and returned as DOCX bytes.

---

## Credits

- OCR model: [Qari by NAMAA Space](https://huggingface.co/NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct)
- Built by [@asabryy](https://github.com/asabryy)
