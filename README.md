# MaatiGyan (মাটিজ্ঞান) — Satellite-Powered Soil Intelligence

**MaatiGyan** delivers free, personalized soil health reports to smallholder farmers via WhatsApp, using Sentinel-2 satellite imagery, an ML spectral model, and a RAG-powered crop recommendation engine — all in Bangla.

---

## 🚀 Simulation & Demo Mode

The system is built to be **runnable immediately** without external API credentials (GEE, WhatsApp, Groq) thanks to its integrated **Simulation Mode**. 

### 1. Quick Start (Local)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ingest RAG data (loads SRDI/BARC fertilizer corpus)
python scripts/ingest_rag_data.py

# 3. Start the FastAPI Backend
uvicorn backend.main:app --reload
```

### 2. Launch the Dashboard
Open `dashboard/index.html` in any modern browser.
- **Interactivity**: Click anywhere on the map of Bangladesh to trigger a live "Satellite → ML → RAG" analysis.
- **Bangla Reports**: View the generated reports in real-time on the administrative feed.
- **Simulate Button**: Use the "Simulate Analysis" button in the top-right to quickly generate random field reports.

---

## 🛠️ Technology Stack
- **Satellite**: Google Earth Engine (Sentinel-2 L2A Harmonized)
- **Backend**: FastAPI (Python 3.11)
- **ML Engine**: Spectral Regression (SOC, Moisture, Nitrogen, Waterlogging)
- **RAG Engine**: Llama-Index + Groq (Llama 3.1 8B) + Qdrant Vector DB
- **Messaging**: Meta WhatsApp Business Cloud API
- **Voice**: gTTS (Google Text-to-Speech) for Bangla Voice Notes
- **Dashboard**: Vanilla JS + Leaflet.js + Glassmorphism CSS

---

## 🏗️ Project Structure
```text
MaatiGyan/
├── backend/
│   ├── main.py              # FastAPI app + WhatsApp webhook
│   ├── config.py            # Pydantic Settings & Environment
│   ├── gee_module.py        # GEE Sentinel-2 Fetcher (Demo + Live)
│   ├── ml_module.py         # Spectral Analysis & Soil Prediction
│   ├── rag_module.py        # Qdrant/Groq Fertilizer Recommendations
│   ├── response_builder.py  # Bangla Report & Voice Note Generator
│   ├── whatsapp_client.py   # Meta Cloud API Handler
│   └── data/                # SRDI Corpus & ML Coefficients
├── dashboard/             # Premium Admin Dashboard (HTML/CSS/JS)
├── scripts/               # Data Ingestion & Model Training
├── requirements.txt
├── Dockerfile
└── README.md
```

---

### 🚀 Production Deployment (Cloud)

MaatiGyan is ready for one-click deployment to **Render** or **Railway**. To go live:

1.  **Connect to GitHub**: Push this repository to your GitHub account.
2.  **Create Web Service**: In Render, click "New + Service" from the Blueprint (`render.yaml`).
3.  **Configure Env Vars**: Add the following secrets in your dashboard:
    - `GROQ_API_KEY`: Your Groq Cloud key.
    - `GEE_SERVICE_ACCOUNT`: Your service account email.
    - `GEE_SERVICE_ACCOUNT_JSON`: The contents of your `gee_service_account_key.json`.
    - `QDRANT_URL` / `QDRANT_API_KEY`: Your Qdrant Cloud details.
4.  **Go Live**: Your app will be live at `https://your-app.onrender.com/farmer/`.

---

### 📶 Local Field Testing

For testing in the field using your laptop as a server:
1.  **Start Server**: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2.  **Mobile Access**: Join the same Wi-Fi and visit `http://[YOUR_IP]:8000/farmer/` on your phone.
3.  **GPS**: Click "Allow" on location permissions to pin your field.

---

## 🚀 Production Deployment (Docker)

MaatiGyan is fully containerized and production-ready.

### 1. Prerequisites
- Docker & Docker Compose installed.
- Valid API keys in `.env`.
- GEE Service Account JSON at `backend/gee_service_account_key.json`.

### 2. Launch with Docker Compose
From the project root, run:
```bash
docker-compose up --build -d
```
This will:
1. Build the MaatiGyan image.
2. Mount a persistent volume for the **Audio Cache** (Voice Notes).
3. Start the FastAPI server on `port 8000`.

### 3. Verify Deployment
- **API Health**: `http://your-server-ip:8000/`
- **Dashboard**: Open `dashboard/index.html` (ensure the API URL in `dashboard/app.js` points to your server's IP).

---

## 🛠️ Security & Maintenance
- **Secrets**: The `.dockerignore` and `.gitignore` files automatically exclude your `.env` and GEE keys from the image and repository tracking.
- **Logs**: View live container logs: `docker logs -f maatigyan_api`.
- **Audio Cleanup**: Periodically clear the `audio_cache/` directory to save disk space if necessary.

---

## 📝 License
Created for Bangladeshi farmers. Proprietary/Educational Use only.
_MaatiGyan — "Empowering Farmers with Space-Age Intelligence."_
