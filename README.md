# Arabic OCR Web App

A web-based tool to convert Arabic PDF files (with diacritical marks) into editable Word documents using the Qwen2-VL vision-language model.

---

## 🧩 Features
- Upload Arabic PDFs from browser
- Extracts text using vision-language OCR (Qwen2-VL)
- Converts result to `.docx` format
- Download Word doc from browser

---

## 🏗️ Project Structure

### Backend (FastAPI)
```
backend/
├── app/
│   ├── main.py                 # Entrypoint
│   ├── api/routes.py           # OCR + download routes
│   ├── core/config.py          # Constants and paths
│   ├── services/               # OCR, PDF and DOCX logic
│   └── utils/logger.py         # Logging setup
├── uploads/                   # Uploaded PDFs
├── output/                    # Generated DOCX files
├── requirements.txt
└── Dockerfile
```

### Frontend (React)
```
frontend/
├── src/
│   ├── components/             # FileUpload, Loader, DownloadLink
│   ├── services/api.js         # Axios logic
│   ├── styles/index.css        # Global styling
│   ├── App.js, index.js
├── public/
├── package.json
└── Dockerfile
```

---

## 🚀 Getting Started (Local Dev with WSL)

### 1. Clone the repository
```bash
git clone https://github.com/asabryy/arabic-ocr-web.git
cd arabic-ocr-web
```

### 2. Backend Setup (WSL)
```bash
cd backend
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Runs on `http://localhost:8000`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm start
```
Runs on `http://localhost:3000`

---

## 🐳 Dockerized Dev/Test
```bash
# Build and start
docker-compose -f docker-compose.dev.yml up --build

# Tear down
docker-compose -f docker-compose.dev.yml down
```

---

## 👥 Contributing
If you’re developing or testing:
- Create a new branch from `dev`
- Use modular files in `/app/services/`, `/components/`, etc.
- Commit small, testable changes

---

## 📄 License
MIT

---

## ✨ Credits
- Qwen2-VL model from [NAMAA Space](https://huggingface.co/NAMAA-Space/Qari-OCR-0.2.2.1-VL-2B-Instruct)
- Developed by [@asabryy](https://github.com/asabryy)
