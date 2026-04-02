"""
MaatiGyan — Google Earth Engine Module
Fetches Sentinel-2 spectral band data for a given coordinate.

DEMO MODE (default): Returns pre-computed, district-calibrated values
LIVE MODE: Queries GEE COPERNICUS/S2_SR_HARMONIZED collection

Both modes return identical data structures so the rest of the pipeline
works unchanged regardless of mode.
"""
import json
import logging
import math
import random
from dataclasses import dataclass
from typing import Optional
import os

logger = logging.getLogger(__name__)


@dataclass
class SentinelBands:
    """Sentinel-2 L2A Surface Reflectance band values (scaled 0–1)"""
    B4: float   # Red (665nm)
    B8: float   # NIR (842nm)
    B11: float  # SWIR1 (1610nm)
    B12: float  # SWIR2 (2190nm)
    lat: float
    lon: float
    district_name: str
    district_name_bn: str
    acquisition_date: str
    cloud_cover: float
    data_source: str  # "gee_live" | "gee_demo"


def _load_demo_districts(coefficients_path: str) -> dict:
    """Load pre-computed district data from soil_coefficients.json"""
    with open(coefficients_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("demo_districts", {})


def _find_nearest_demo_district(lat: float, lon: float, districts: dict) -> tuple[str, dict]:
    """Find the closest demo district to the given coordinates using Haversine distance"""
    best_dist = float("inf")
    best_key = "bogura"
    best_data = None

    for key, d in districts.items():
        dlat = math.radians(d["lat"] - lat)
        dlon = math.radians(d["lon"] - lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(d["lat"])) * math.sin(dlon / 2) ** 2
        dist = 2 * math.asin(math.sqrt(a)) * 6371  # km
        if dist < best_dist:
            best_dist = dist
            best_key = key
            best_data = d

    return best_key, best_data


def fetch_sentinel2_demo(
    lat: float,
    lon: float,
    coefficients_path: str,
    noise_factor: float = 0.05,
) -> SentinelBands:
    """
    Demo mode: Return pre-calibrated Sentinel-2 band values for the
    nearest Bangladesh district with small realistic noise added.
    """
    from datetime import datetime, timedelta
    import random

    districts = _load_demo_districts(coefficients_path)
    district_key, district_data = _find_nearest_demo_district(lat, lon, districts)

    # Add small Gaussian noise to simulate real variability
    rng = random.Random(hash(f"{lat:.3f}{lon:.3f}"))

    def noisy(val: float) -> float:
        return max(0.001, val + rng.gauss(0, val * noise_factor))

    # Simulate recent acquisition date
    acquisition_date = (
        datetime.now() - timedelta(days=rng.randint(1, 5))
    ).strftime("%Y-%m-%d")

    return SentinelBands(
        B4=noisy(district_data["B4"]),
        B8=noisy(district_data["B8"]),
        B11=noisy(district_data["B11"]),
        B12=noisy(district_data["B12"]),
        lat=lat,
        lon=lon,
        district_name=district_key.capitalize(),
        district_name_bn=district_data["name_bn"],
        acquisition_date=acquisition_date,
        cloud_cover=rng.uniform(2.0, 12.0),
        data_source="gee_demo",
    )


def fetch_sentinel2_live(
    lat: float,
    lon: float,
    gee_service_account: str,
    gee_key_file: str,
    gee_service_account_json: Optional[str] = None,
) -> Optional[SentinelBands]:
    """
    Live mode: Query GEE COPERNICUS/S2_SR_HARMONIZED for recent
    cloud-free imagery at the given coordinates.
    Returns None if GEE query fails (caller should fall back to demo).
    """
    try:
        # Authenticate with service account (File or JSON string)
        if gee_service_account_json:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(gee_service_account_json)
                temp_path = f.name
            try:
                credentials = ee.ServiceAccountCredentials(gee_service_account, temp_path)
                ee.Initialize(credentials)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            credentials = ee.ServiceAccountCredentials(gee_service_account, gee_key_file)
            ee.Initialize(credentials)

        point = ee.Geometry.Point([lon, lat])
        # 1km buffer for pixel sampling
        region = point.buffer(500)

        # Get most recent cloud-free Sentinel-2 image (last 30 days, <20% cloud)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(
                ee.Date(ee.Date.now().advance(-30, "day")),
                ee.Date.now(),
            )
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
            .sort("system:time_start", False)
        )

        image = collection.first()
        if image is None:
            logger.warning("GEE: No cloud-free Sentinel-2 image found in last 30 days")
            return None

        # Sample spectral bands at the point
        bands = ["B4", "B8", "B11", "B12"]
        sample = image.select(bands).sample(region=point, scale=20, numPixels=1)
        values = sample.first().getInfo()["properties"]

        # GEE Sentinel-2 SR values are scaled 0–10000 → normalize to 0–1
        scale = 10000.0

        # Get image metadata
        info = image.getInfo()
        props = info.get("properties", {})
        date_ms = props.get("system:time_start", 0)
        from datetime import datetime
        acq_date = datetime.fromtimestamp(date_ms / 1000).strftime("%Y-%m-%d")

        return SentinelBands(
            B4=values["B4"] / scale,
            B8=values["B8"] / scale,
            B11=values["B11"] / scale,
            B12=values["B12"] / scale,
            lat=lat,
            lon=lon,
            district_name="Live",
            district_name_bn="লাইভ তথ্য",
            acquisition_date=acq_date,
            cloud_cover=props.get("CLOUDY_PIXEL_PERCENTAGE", 0.0),
            data_source="gee_live",
        )

    except ImportError:
        logger.error("earthengine-api not installed. Run: pip install earthengine-api")
        return None
    except Exception as e:
        logger.error(f"GEE query failed: {e}")
        return None


def get_sentinel2_bands(
    lat: float,
    lon: float,
    coefficients_path: str,
    demo_mode: bool = True,
    gee_service_account: str = "",
    gee_key_file: str = "",
    gee_service_account_json: Optional[str] = None,
) -> SentinelBands:
    """
    Main entry point. Tries live GEE if configured, falls back to demo mode.
    """
    # Validate Bangladesh coordinates (approximate bounding box)
    if not (20.5 <= lat <= 26.7 and 88.0 <= lon <= 92.7):
        logger.warning(f"Coordinates ({lat}, {lon}) outside Bangladesh bounds. Using demo data.")
        demo_mode = True

    if not demo_mode and gee_service_account:
        logger.info("Attempting live GEE query...")
        live_result = fetch_sentinel2_live(
            lat, lon, 
            gee_service_account, 
            gee_key_file,
            gee_service_account_json=gee_service_account_json
        )
        if live_result:
            return live_result

    logger.info(f"Using demo Sentinel-2 data for ({lat:.4f}, {lon:.4f})")
    return fetch_sentinel2_demo(lat, lon, coefficients_path)
