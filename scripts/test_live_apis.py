"""
MaatiGyan — Live API Connectivity Test
Verifies Groq, GEE, and Qdrant Cloud connectivity.
"""
import logging
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LiveTester")

async def test_groq(settings):
    logger.info("Testing Groq API...")
    try:
        from llama_index.llms.groq import Groq
        llm = Groq(model=settings.groq_model, api_key=settings.groq_api_key)
        response = llm.complete("Hello, are you online? Answer in one word.")
        logger.info(f"✅ Groq Online: {response.text.strip()}")
        return True
    except Exception as e:
        logger.error(f"❌ Groq Failed: {e}")
        return False

def test_gee(settings):
    logger.info("Testing Google Earth Engine...")
    try:
        import ee
        # Authenticate
        credentials = ee.ServiceAccountCredentials(settings.gee_service_account, settings.gee_key_file)
        ee.Initialize(credentials)
        
        # Simple query: Get info of a single point in Bangladesh
        point = ee.Geometry.Point([90.4125, 23.8103])
        info = point.getInfo()
        logger.info(f"✅ GEE Online: Connected to project '{settings.gee_service_account.split('@')[1].split('.')[0]}'")
        return True
    except Exception as e:
        logger.error(f"❌ GEE Failed: {e}")
        return False

def test_qdrant(settings):
    logger.info(f"Testing Qdrant Cloud at {settings.qdrant_url}...")
    try:
        import qdrant_client
        client = qdrant_client.QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        # Get collections
        collections = client.get_collections()
        logger.info(f"✅ Qdrant Online: Found {len(collections.collections)} collections")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant Failed: {e}")
        return False

async def main():
    settings = get_settings()
    logger.info("--- Starting Live API Tests ---")
    
    groq_ok = await test_groq(settings)
    gee_ok = test_gee(settings)
    qdrant_ok = test_qdrant(settings)
    
    logger.info("--- Test Summary ---")
    logger.info(f"Groq: {'PASS' if groq_ok else 'FAIL'}")
    logger.info(f"GEE: {'PASS' if gee_ok else 'FAIL'}")
    logger.info(f"Qdrant: {'PASS' if qdrant_ok else 'FAIL'}")
    
    if all([groq_ok, gee_ok, qdrant_ok]):
        logger.info("🚀 ALL SYSTEMS GO! MaatiGyan is now LIVE.")
    else:
        logger.warning("⚠️ Some systems failed. Check your credentials.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
