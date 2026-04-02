"""
MaatiGyan — Live Analysis Trigger for Chuadanga
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import process_soil_analysis
from backend.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChuadangaRunner")

async def main():
    # Chuadanga Center Coordinates
    lat, lon = 23.6416, 88.8475
    crop = "boro_rice"
    
    logger.info("--- 🌏 MAATIGYAN LIVE RUN: CHUADANGA ---")
    
    try:
        # We try to run the analysis pipeline
        # Note: If dependencies are missing, this will fail with ImportError
        result = await process_soil_analysis(
            lat=lat, 
            lon=lon, 
            crop=crop, 
            district_code="CHU",
            language="bn"
        )
        
        print("\n" + "="*40)
        print("🌱 LIVE REPORT FOR CHUADANGA")
        print("="*40)
        print(result["report"]["text"])
        print("="*40)
        print(f"⏱️ Analysis Time: {result['performance']['duration_seconds']}s")
        print("="*40)
        
    except ImportError as e:
        logger.error(f"❌ Dependency Error: {e}. Please ensure 'pip install -r requirements.txt' succeeded.")
    except Exception as e:
        logger.error(f"❌ Analysis Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
