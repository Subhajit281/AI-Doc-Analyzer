# Free-Tier Deployment Guide (512 MB Allowance)

This project has been optimized to run reliably within **512 MB RAM** free-tier platforms such as **Render**, **Railway**, and **Fly.io**.

---

## Key Optimizations Active in Free-Tier Mode

1. **Lightweight Document Parser**: Replaces heavy vision models (DocLayNet, RT-DETR, TableFormer) with native C-based `pypdfium2`, `python-docx`, `python-pptx`, `openpyxl`, and `beautifulsoup4`. Memory drops from **1,100 MB** to **< 30 MB**.
2. **Zero-RAM Gemini Embeddings**: Vector embeddings use Google's official `models/gemini-embedding-001` via your existing `GEMINI_API_KEY`. Saves **450 MB** of local model weights.
3. **Async Ingestion Queue**: Queues concurrent uploads sequentially to prevent simultaneous memory spikes.
4. **Multi-Layer LRU Caching**: In-memory caching for `manifest.json` and query vector embeddings.
5. **Linux OS Heap Trimming**: Runs `malloc_trim(0)` and `gc.collect()` after each ingestion and query to release heap pages back to the host operating system.
6. **glibc Arena Limiter**: `MALLOC_ARENA_MAX=2` prevents memory fragmentation inside Docker containers.

---

## Option 1: Deploy to Render (Free Web Service)

1. Create a new **Web Service** on [Render Dashboard](https://dashboard.render.com/).
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-free-tier.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
4. Set Environment Variables:
   - `GEMINI_API_KEY`: `your_gemini_api_key_here`
   - `PARSER_BACKEND`: `lightweight`
   - `EMBEDDING_PROVIDER`: `gemini`
   - `MALLOC_ARENA_MAX`: `2`
   - `PYTHONUNBUFFERED`: `1`
5. Click **Deploy Web Service**. Build will finish in under 2 minutes (compared to 15+ minutes with PyTorch).

---

## Option 2: Deploy to Railway

1. Install Railway CLI or connect via GitHub on [Railway.app](https://railway.app/).
2. Set root directory to `backend`.
3. Set the environment variables (`GEMINI_API_KEY`, etc.).
4. Railway will automatically detect the `Dockerfile` and deploy with minimal resource consumption.

---

## Option 3: Deploy via Docker (Local or Any VPS)

```bash
cd backend
docker build -t document-ai-backend .
docker run -d -p 8000:8000 -e GEMINI_API_KEY="your_api_key" --memory="512m" document-ai-backend
```

---

## Switching Back to Heavy Docling Mode (Optional)

If you ever deploy on a larger server (>= 4 GB RAM) or want to run IBM Docling's vision models:
- Set environment variable: `PARSER_BACKEND=docling`
- Set environment variable: `EMBEDDING_PROVIDER=local` (if you want local HuggingFace embeddings)
- Install standard `requirements.txt` instead of `requirements-free-tier.txt`.

