# AI Product Recommendation MVP

This is a full-stack AI web app built with **FastAPI (backend)** and **React + Vite (frontend)**.

## 📦 Features
- Semantic product recommendations (Sentence-Transformers + FAISS + LangChain)
- Zero-shot image classification with CLIP
- Creative product description generation (DistilGPT-2)
- Analytics dashboard for category & price insights

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv
# activate
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
