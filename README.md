# Textara — Arabic OCR Web App

Converts Arabic PDFs into editable Word documents using Google's Gemini vision model for OCR.

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
| `doc-worker` | RabbitMQ consumer + in-process OCR (renders PDF, calls Gemini, builds RTL DOCX) | k3s |
| `rabbitmq` | Message broker for OCR task queue | k3s StatefulSet |

All traffic routes through an Nginx ingress on a k3s cluster hosted on Oracle Cloud Free Tier:
- `/api/auth/` → `auth-service`
- `/api/doc-manager/` → `doc-manager`
- `/` → `frontend`

The OCR runs in-process inside the `doc-worker`: each PDF page is rendered to an image and sent to Google's Gemini vision model, and the transcribed text is assembled into a right-to-left Word document. No GPU required. The provider lives behind a single seam (`app/ocr/pipeline.py` + `OCR_BACKEND`), so it can be swapped without touching the queue or storage layers.

---

## Credits

- OCR: [Google Gemini](https://ai.google.dev/) vision model
- Built by [@asabryy](https://github.com/asabryy)
