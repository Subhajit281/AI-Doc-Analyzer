# 🚀 Document AI Analyzer - Production Deployment Guide

This guide details how to deploy the **Document AI Analyzer** full-stack application to free-tier cloud platforms.

```
┌───────────────────────────────┐
│     Frontend (Vercel / CDN)   │  React + Vite SPA
│   https://your-app.vercel.app │
└───────────────┬───────────────┘
                │ HTTPS (CORS enabled)
                ▼
┌───────────────────────────────┐
│     Backend (Render Web Svc)  │  FastAPI (<= 512 MB RAM allowance)
│  https://your-api.onrender.com│  Lightweight parser + Gemini Embeddings
└───────────────┬───────────────┘
                │
    ┌───────────┼───────────┬─────────────┬─────────────┐
    ▼           ▼           ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌───────────┐
│ MongoDB │ │  Groq   │ │ Gemini  │ │  EmailJS  │ │ Razorpay  │
│  Atlas  │ │ LLM API │ │ Embeds  │ │  OTP Auth │ │ Payments  │
└─────────┘ └─────────┘ └─────────┘ └───────────┘ └───────────┘
```

---

## 📋 Required Environment Variables

When deploying the backend web service, set the following environment variables in your cloud provider's dashboard:

| Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq API Key | `gsk_...` |
| `GROQ_FREE_MODEL` | Free tier LLM model | `openai/gpt-oss-120b` |
| `GROQ_PRO_MODEL` | Upgraded tier LLM model | `qwen/qwen3.8-27b` |
| `GEMINI_API_KEY` | Google Gemini API Key (Embeddings) | `AIzaSy...` |
| `MONGODB_URI` | MongoDB Atlas Connection String | `mongodb+srv://user:pass@cluster0...` |
| `MONGODB_DB_NAME` | Database name | `document_ai` |
| `RAZORPAY_KEY_ID` | Razorpay Key ID | `rzp_test_...` (or live key) |
| `RAZORPAY_KEY_SECRET` | Razorpay Secret | `...` |
| `RAZORPAY_MERCHANT_UPI` | UPI ID for modal display | `yourname@upi` |
| `SENDER_EMAIL` | Email used in OTP sender field | `your_email@gmail.com` |
| `EMAILJS_SERVICE_ID` | EmailJS Service ID | `service_...` |
| `EMAILJS_TEMPLATE_ID` | EmailJS Template ID | `template_...` |
| `EMAILJS_PUBLIC_KEY` | EmailJS Public API Key | `...` |
| `EMAILJS_PRIVATE_KEY`| EmailJS Private API Key | `...` |
| `PARSER_BACKEND` | Memory-optimized parser | `lightweight` *(strictly required for 512 MB)* |
| `EMBEDDING_PROVIDER` | Cloud embedding provider | `gemini` *(0 MB local RAM usage)* |
| `MALLOC_ARENA_MAX` | glibc memory fragmentation cap | `2` |
| `PYTHONUNBUFFERED` | Unbuffered stdout/stderr | `1` |
| `ALLOWED_ORIGINS` | Allowed frontend URLs (comma-separated)| `https://your-app.vercel.app` *(optional)* |

---

## 🌟 Method 1 (Recommended): Render (Backend) + Vercel (Frontend)

This is the fastest, most reliable architecture: Vercel provides instant global edge CDN hosting with zero cold starts for the React UI, while Render hosts the Python FastAPI container.

### Step 1: Push Your Code to GitHub
Ensure all latest changes are committed and pushed:
```bash
git add .
git commit -m "chore: configure production deployment and dependencies"
git push origin main
```

### Step 2: Deploy Backend to Render (Free Web Service)
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Web Service**.
2. Connect your GitHub repository (`Subhajit281/AI-Doc-Analyzer`).
3. Configure the settings:
   - **Name**: `document-ai-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements-free-tier.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Instance Type**: **Free** (512 MB RAM)
4. Under **Advanced** → **Add Environment Variable**, add the required environment variables listed in the table above.
5. Click **Deploy Web Service**.
6. Once deployed, copy your backend URL (e.g., `https://document-ai-backend-xxxx.onrender.com`).
   - Test it by opening `https://document-ai-backend-xxxx.onrender.com/docs` in your browser.

### Step 3: Deploy Frontend to Vercel
1. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New...** → **Project**.
2. Import your GitHub repository (`Subhajit281/AI-Doc-Analyzer`).
3. In the project configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and choose `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://document-ai-backend-xxxx.onrender.com` *(your Render backend URL with NO trailing slash)*
5. Click **Deploy**.
6. Vercel will build the frontend in ~30 seconds and provide your live URL (e.g., `https://ai-doc-analyzer.vercel.app`).

---

## ⚡ Method 2: 1-Click Render Blueprint (All on Render)

If you prefer managing everything in a single Render dashboard:

1. Push the repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com/), click **New +** → **Blueprint**.
3. Select your repository (`Subhajit281/AI-Doc-Analyzer`).
4. Render will detect `render.yaml` and configure:
   - `document-ai-backend` (Web Service)
   - `document-ai-frontend` (Static Site with automatic route linking)
5. Fill in the non-synced secret environment variables when prompted.
6. Click **Apply**. Both services will build and deploy automatically.

---

## 🐳 Method 3: Deploy via Docker (Railway, Fly.io, or VPS)

A production-ready, multi-stage `Dockerfile` is included in `backend/`:

```bash
cd backend
docker build -t document-ai-backend .
docker run -d -p 8000:8000 --env-file .env --memory="512m" document-ai-backend
```

---

## 🔍 Post-Deployment Verification Checklist

Once deployed, perform this quick end-to-end verification:
- [ ] **Health & Docs**: Open `https://your-backend.onrender.com/docs` — Swagger UI loads.
- [ ] **Auth Gate**: Open the frontend URL — Unauthenticated users are immediately presented with the Sign In / Sign Up modal.
- [ ] **OTP Delivery**: Enter your email address — Verify that the 6-digit OTP arrives in your inbox and authenticates you.
- [ ] **Document Upload**: Upload a PDF or DOCX file — Verify upload succeeds and remaining TTL displays as `Expires in 7d`.
- [ ] **Chat / Query**: Ask questions about the document — Responses stream in using the free-tier model.
- [ ] **Quota & Monetization**: Verify the query count updates dynamically (`10 left today`).
- [ ] **Pro Upgrade**: Open pricing modal and trigger test payment to verify upgraded access.

