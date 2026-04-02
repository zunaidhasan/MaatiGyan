"""
MaatiGyan — FastAPI Application
The central hub for satellite-powered soil intelligence.
Connects WhatsApp webhooks to the GEE-ML-RAG pipeline.
"""
import logging
import time
from typing import Optional

from fastapi import FastAPI, Request, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_settings
from .gee_module import get_sentinel2_bands
from .ml_module import predict_soil_health
from .rag_module import get_fertilizer_recommendation
from .response_builder import build_soil_report
from .whatsapp_client import (
    send_text_message,
    send_audio_message,
    send_reaction,
    parse_webhook_location,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MaatiGyan")

# Initialize app
app = FastAPI(
    title="MaatiGyan Soil Intelligence API",
    version="1.0.0",
)

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the dashboard domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
SETTINGS = get_settings()

# Mount Static Files (Farmer App and Dashboard)
app.mount("/farmer", StaticFiles(directory="farmer", html=True), name="farmer")
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


# ─── Request Models ──────────────────────────────────────────────────────────

class FarmerAnalysisRequest(BaseModel):
    """Input for the Farmer Web App"""
    lat: float
    lon: float
    farmer_name: str
    land_area: float  # In Bighas
    crop: str = "boro_rice"
    language: str = "bn"


# ─── Pipeline Logic ─────────────────────────────────────────────────────────

async def process_soil_analysis(
    lat: float,
    lon: float,
    phone_number: Optional[str] = None,
    msg_id: Optional[str] = None,
    crop: str = "boro_rice",
    district_code: str = "GEN",
    language: str = "bn",
    farmer_name: Optional[str] = None,
    land_area: float = 1.0,
) -> dict:
    """
    The main execution pipeline:
    1. GEE (Satellite) → 2. ML (Soil Params) → 3. RAG (Ferts) → 4. Response Builder
    """
    start_time = time.time()
    logger.info(f"🚀 Starting analysis for ({lat}, {lon}) | Crop: {crop}")

    # Step 1: Satellite Data Fetch (Sentinel-2)
    bands = get_sentinel2_bands(
        lat=lat,
        lon=lon,
        coefficients_path=SETTINGS.soil_coefficients_path,
        demo_mode=SETTINGS.demo_mode,
        gee_service_account=SETTINGS.gee_service_account,
        gee_key_file=SETTINGS.gee_key_file,
        gee_service_account_json=SETTINGS.gee_service_account_json,
    )

    # Step 2: ML Prediction (Soil Health)
    prediction = predict_soil_health(
        bands=bands,
        coefficients_path=SETTINGS.soil_coefficients_path,
        crop=crop,
    )

    # Step 3: RAG Retrieval (Fertilizer Recommendations)
    recommendation = get_fertilizer_recommendation(
        soc_level=prediction.soc.level,
        nitrogen_level=prediction.nitrogen.level,
        moisture_level=prediction.moisture_stress.level,
        crop=crop,
        district=bands.district_name,
        groq_api_key=SETTINGS.groq_api_key,
        corpus_path=SETTINGS.srdi_corpus_path,
        qdrant_url=SETTINGS.qdrant_url,
        qdrant_api_key=SETTINGS.qdrant_api_key,
    )

    # Step 4: Build Report (Text + Voice)
    report = build_soil_report(
        prediction=prediction,
        recommendation=recommendation,
        district_name_bn=bands.district_name_bn,
        district_code=district_code,
        lat=lat,
        lon=lon,
        acquisition_date=bands.acquisition_date,
        data_source=bands.data_source,
        audio_dir=SETTINGS.audio_dir,
        generate_audio=True,
        language=language,
        farmer_name=farmer_name,
        land_area=land_area,
    )

    duration = time.time() - start_time
    logger.info(f"✅ Analysis complete in {duration:.2f}s | Report ID: {report.report_id}")

    # Step 5: (Optional) Deliver via WhatsApp
    if phone_number and SETTINGS.is_whatsapp_configured:
        # Send acknowledgement reaction first
        if msg_id:
            await send_reaction(phone_number, msg_id, "🌱", 
                              SETTINGS.whatsapp_phone_number_id, SETTINGS.whatsapp_token)

        # Send text report
        success = await send_text_message(
            phone_number, report.text_report,
            SETTINGS.whatsapp_phone_number_id, SETTINGS.whatsapp_token,
            demo_mode=SETTINGS.demo_mode
        )

        # Send audio if generated (requires public URL in non-demo mode)
        # Note: In demo mode, we usually rely on logging for visibility
        if success and report.audio_path:
             logger.info(f"Audio note generated at: {report.audio_path}")

    return {
        "report_id": report.report_id,
        "status": "success",
        "coordinates": {"lat": lat, "lon": lon},
        "district": bands.district_name_bn,
        "prediction": prediction,
        "recommendation": recommendation,
        "report": {
            "text": report.text_report,
            "summary": report.summary_line,
            "audio_available": bool(report.audio_path)
        },
        "performance": {"duration_seconds": round(duration, 2)}
    }


# ─── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": SETTINGS.app_name,
        "version": SETTINGS.app_version,
        "status": "online",
        "demo_mode": SETTINGS.demo_mode,
        "configured_apis": {
            "whatsapp": SETTINGS.is_whatsapp_configured,
            "gee": SETTINGS.is_gee_configured,
            "groq": SETTINGS.is_groq_configured
        }
    }


@app.get("/webhook")
async def verify_webhook(
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp Cloud API Webhook Verification."""
    if token == SETTINGS.whatsapp_verify_token:
        return PlainTextResponse(challenge)
    return JSONResponse(content={"error": "Invalid verify token"}, status_code=403)


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handles incoming WhatsApp messages.
    When a farmer shares location, triggers the soil analysis pipeline.
    """
    try:
        payload = await request.json()
        logger.info(f"Received webhook: {payload}")

        data = parse_webhook_location(payload)
        if not data:
            return {"status": "ignored"}

        # If it's a location message
        if "lat" in data and "lon" in data:
            background_tasks.add_task(
                process_soil_analysis,
                lat=data["lat"],
                lon=data["lon"],
                phone_number=data["phone_number"],
                msg_id=data["message_id"]
            )
            return {"status": "processing"}

        # Handle text triggers (e.g., "start", "help")
        if data.get("type") == "text":
            text = data["text"]
            if text in ["সালাম", "hello", "hi", "start"]:
                await send_text_message(
                    data["phone_number"],
                    "🌱 *স্বাগতম মাটিজ্ঞান-এ!* আমি আপনাকে আপনার জমির মাটির স্বাস্থ্য জানাতে সাহায্য করবো।\n\nঅনুগ্রহ করে হোয়াটসঅ্যাপের মাধ্যমে আপনার *জমির লোকেশন* শেয়ার করুন।",
                    SETTINGS.whatsapp_phone_number_id, SETTINGS.whatsapp_token,
                    demo_mode=SETTINGS.demo_mode
                )
            return {"status": "replied"}

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/analyze")
async def manual_analyze(lat: float, lon: float, crop: str = "boro_rice"):
    """Trigger analysis for the dashboard."""
    try:
        result = await process_soil_analysis(lat, lon, crop=crop)
        return result
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/farmer-analyze")
async def farmer_analyze(request: FarmerAnalysisRequest):
    """
    Personalized analysis for the Farmer Web App.
    Accepts Name, Land Area, and Live GPS coords.
    """
    try:
        result = await process_soil_analysis(
            lat=request.lat,
            lon=request.lon,
            farmer_name=request.farmer_name,
            land_area=request.land_area,
            crop=request.crop,
            language=request.language
        )
        return result
    except Exception as e:
        logger.error(f"Farmer analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo-request")
async def simulate_demo_request():
    """Simulates a farmer sending a location from Bogura for rapid demo."""
    # Bogura coordinate
    lat, lon = 24.8481, 89.3730
    return await process_soil_analysis(lat, lon, phone_number="8801700000000")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SETTINGS.app_host, port=SETTINGS.app_port)
