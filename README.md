# Arabic OCR Web App (Qwen2-VL)

This is a full-stack Arabic OCR (Optical Character Recognition) web application that converts Arabic PDF files — including **diacritics (Tashkeel)** — into downloadable `.docx` Word documents. It uses **Qwen2-VL**, a vision-language model, for accurate text extraction, and supports GPU acceleration via Docker.

---

## 🧱 Project Structure

```
arabic-ocr-web/
├── backend/           # FastAPI + Qwen2-VL backend
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # React frontend with Tailwind styling
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml # Orchestrates frontend + backend
```

---

## 🚀 Features

- Upload Arabic PDFs through a modern web interface
- Uses Qwen2-VL for accurate OCR with diacritic support
- Converts extracted text into structured `.docx` documents
- Download the result directly from the web app
- GPU-accelerated backend using NVIDIA Docker (CUDA 12.1)
- Frontend built with React + Tailwind (ready for customization)

---

## 🖥 Requirements

- Docker and Docker Compose
- NVIDIA GPU with drivers + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

---

## ⚙️ Setup Instructions

### 1. Clone the Repo & Build

```
git clone https://github.com/your-repo/arabic-ocr-web.git
cd arabic-ocr-web
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### 2. Upload a PDF

- Go to the frontend (`localhost:3000`)
- Upload a PDF
- Wait for OCR processing
- Download the generated `.docx`

---

## 🧠 Backend Overview

- Built using **FastAPI**
- OCR via **Qwen2-VL model** loaded from HuggingFace
- Converts PDF to images using `pdf2image`
- For each page:
  - Prompt sent to Qwen2-VL
  - Text extracted with diacritics
  - Structured into `.docx` with Python `docx` library
- File returned as HTTP response

---

## 🌐 Frontend Overview

- Built using **React + Axios**
- Uploads PDF to `/upload` backend endpoint
- Receives `.docx` as Blob
- Shows download link
- Tailwind CSS for styling

---

## 🐳 Docker Setup Details

### Backend (FastAPI + Torch + Qwen2-VL)
- Base image: `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- Installs `torch`, `transformers`, `pdf2image`, etc.
- Runs `uvicorn` server on port `8000`

### Frontend (React + Nginx)
- Build: `npm run build`
- Serve: Nginx on port `3000`

---

## ✅ Customization

- Modify `main.py` to change:
  - OCR prompt
  - PDF → DOCX layout logic
- Modify React in `frontend/src/` for new features or layout

---

## 🛠 Development Notes

- To rebuild after backend changes:
  ```
  docker compose build backend
  docker compose up
  ```

- To add persistent volume:
  ```
  volumes:
    - ./backend/uploads:/app/uploads
  ```

---

## 📦 Deployment Options

- Run locally (default)
- Host on AWS EC2, RunPod, or Paperspace (GPU required)
- Bundle as desktop app with Tauri or Electron (future step)

---

## 📄 License

MIT — use freely with credit.

---

## 👤 Author

Built by Ahmed Ahmed — powered by OpenAI and Qwen2-VL
