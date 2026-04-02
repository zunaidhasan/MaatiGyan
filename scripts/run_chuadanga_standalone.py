"""
MaatiGyan — Direct Analysis Run (Chuadanga)
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.config import get_settings
from backend.gee_module import get_sentinel2_bands
from backend.ml_module import predict_soil_health
from backend.rag_module import get_fertilizer_recommendation
from backend.response_builder import build_soil_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChuadangaLive")

async def run_analysis():
    settings = get_settings()
    lat, lon = 23.6416, 88.8475
    crop = "boro_rice"
    
    logger.info(f"🚀 RUNNING LIVE ANALYSIS FOR CHUADANGA ({lat}, {lon})")
    
    # 1. GEE Fetch
    bands = get_sentinel2_bands(
        lat=lat, lon=lon,
        coefficients_path=settings.soil_coefficients_path,
        demo_mode=False, # LIVE MODE
        gee_service_account=settings.gee_service_account,
        gee_key_file=settings.gee_key_file
    )
    logger.info(f"✅ GEE Fetch Success: {bands.data_source} (Cloud: {bands.cloud_cover:.1f}%)")

    # 2. ML Prediction
    prediction = predict_soil_health(bands, settings.soil_coefficients_path, crop)
    logger.info(f"✅ ML Prediction: SOC {prediction.soc.level} ({prediction.soc.value}%)")

    # 3. RAG Recommendation (Uses keyword fallback if LlamaIndex missing)
    recommendation = get_fertilizer_recommendation(
        soc_level=prediction.soc.level,
        nitrogen_level=prediction.nitrogen.level,
        moisture_level=prediction.moisture_stress.level,
        crop=crop,
        district=bands.district_name
    )

    # 4. Build Report
    report = build_soil_report(
        prediction, recommendation,
        district_name_bn=bands.district_name_bn,
        district_code="CHU",
        lat=lat, lon=lon,
        acquisition_date=bands.acquisition_date,
        data_source=bands.data_source,
        audio_dir=settings.audio_dir,
        generate_audio=False # Skip gTTS for now
    )

    with open("scripts/chuadanga_report.txt", "w", encoding="utf-8") as f:
        f.write(report.text_report)
    
    print("\n" + "="*45)
    print("✅ ANALYSIS SUCCESSFUL: CHUADANGA")
    print("="*48)
    print("Report saved to scripts/chuadanga_report.txt")
    print("="*48)

if __name__ == "__main__":
    asyncio.run(run_analysis())
