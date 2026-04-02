"""
MaatiGyan — Simplified API Connectivity Test (No LlamaIndex)
"""
import logging
import httpx
import json
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SimpleTester")

# Get keys from environment
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_KEY = os.getenv("QDRANT_API_KEY", "")
GEE_SA = os.getenv("GEE_SERVICE_ACCOUNT", "")
GEE_KEY_FILE = os.getenv("GEE_KEY_FILE", "backend/gee_service_account_key.json")

async def test_groq():
    logger.info("Testing Groq API (HTTPS)...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "hi"}]
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                logger.info("✅ Groq Connected!")
                return True
            else:
                logger.error(f"❌ Groq Error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Groq Failed: {e}")
            return False

async def test_qdrant():
    logger.info(f"Testing Qdrant Cloud (HTTPS) at {QDRANT_URL}...")
    url = f"{QDRANT_URL}/collections"
    headers = {"api-key": QDRANT_KEY}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                logger.info("✅ Qdrant Connected!")
                return True
            else:
                logger.error(f"❌ Qdrant Error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Qdrant Failed: {e}")
            return False

def test_gee():
    logger.info("Testing GEE (Native Auth)...")
    try:
        import ee
        # Authenticate
        credentials = ee.ServiceAccountCredentials(GEE_SA, GEE_KEY_FILE)
        ee.Initialize(credentials)
        info = ee.Geometry.Point([90.4125, 23.8103]).getInfo()
        logger.info("✅ GEE Connected!")
        return True
    except Exception as e:
        logger.error(f"❌ GEE Failed: {e}")
        return False

async def main():
    logger.info("--- Starting Simple API Tests ---")
    groq_ok = await test_groq()
    qdrant_ok = await test_qdrant()
    # GEE test requires 'ee' package installed
    gee_ok = test_gee()
    
    logger.info("--- Test Summary ---")
    logger.info(f"Groq: {'PASS' if groq_ok else 'FAIL'}")
    logger.info(f"Qdrant: {'PASS' if qdrant_ok else 'FAIL'}")
    logger.info(f"GEE: {'PASS' if gee_ok else 'FAIL'}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
