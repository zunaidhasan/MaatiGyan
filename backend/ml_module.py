"""
MaatiGyan — ML Spectral Analysis Module

Predicts soil health parameters from Sentinel-2 band values using
pre-calibrated linear regression coefficients (derived from LUCAS dataset
correlations, calibrated against SRDI Bangladesh soil maps).

Full Random Forest training workflow is in scripts/train_model.py
"""
import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from .gee_module import SentinelBands

logger = logging.getLogger(__name__)


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class SpectralIndices:
    """Derived spectral indices from Sentinel-2 bands"""
    NDVI: float        # Normalized Difference Vegetation Index
    BSI: float         # Bare Soil Index
    SWIR_ratio: float  # SWIR1/SWIR2 — organic matter proxy
    NDWI: float        # Normalized Difference Water Index (moisture)


@dataclass
class SoilParameter:
    """A single predicted soil parameter with categorical label"""
    value: float
    unit: str
    level: str          # e.g. "LOW", "MEDIUM", "HIGH"
    level_bn: str       # Bangla label
    icon: str           # Emoji indicator
    confidence: str     # "HIGH" | "MEDIUM" | "LOW" — model confidence


@dataclass
class SoilPrediction:
    """Complete soil health prediction for a location"""
    soc: SoilParameter          # Soil Organic Carbon (%)
    nitrogen: SoilParameter     # Nitrogen level
    moisture_stress: SoilParameter  # Moisture stress index
    waterlogging_risk: SoilParameter  # Waterlogging risk (0–1)
    indices: SpectralIndices
    overall_health: str         # "DEGRADED" | "MODERATE" | "GOOD"
    overall_health_bn: str
    savings_estimate: dict = field(default_factory=dict)  # Fertilizer savings vs. common practice


# ─── Spectral Indices Computation ────────────────────────────────────────────

def compute_spectral_indices(bands: SentinelBands) -> SpectralIndices:
    """Compute spectral indices from Sentinel-2 band values"""
    B4, B8, B11, B12 = bands.B4, bands.B8, bands.B11, bands.B12
    # Approximate B2 (Blue) from demo if not available
    B2 = B4 * 0.72  # Empirical ratio common in Bangladesh agricultural areas

    # NDVI — Vegetation health (−1 to +1, higher = more vegetation)
    ndvi_denom = B8 + B4
    NDVI = (B8 - B4) / ndvi_denom if ndvi_denom > 0 else 0.0

    # Bare Soil Index — higher = more bare soil exposed
    bsi_num = (B11 + B4) - (B8 + B2)
    bsi_denom = (B11 + B4) + (B8 + B2)
    BSI = bsi_num / bsi_denom if bsi_denom > 0 else 0.0

    # SWIR ratio — organic matter proxy (lower SWIR = more organic matter)
    SWIR_ratio = B11 / B12 if B12 > 0 else 1.5

    # NDWI — Water content (higher = wetter)
    ndwi_denom = B8 + B11
    NDWI = (B8 - B11) / ndwi_denom if ndwi_denom > 0 else 0.0

    return SpectralIndices(
        NDVI=round(NDVI, 4),
        BSI=round(BSI, 4),
        SWIR_ratio=round(SWIR_ratio, 4),
        NDWI=round(NDWI, 4),
    )


# ─── Prediction Functions ──────────────────────────────────────────────────

def _classify(value: float, thresholds: dict) -> tuple[str, str, str]:
    """Return (level_en, level_bn, icon) based on threshold config"""
    for level_key, cfg in thresholds.items():
        if value <= cfg["max"]:
            return cfg["label_en"], cfg["label_bn"], cfg["icon"]
    # Fallback to last entry
    last = list(thresholds.values())[-1]
    return last["label_en"], last["label_bn"], last["icon"]


def predict_soc(indices: SpectralIndices, bands: SentinelBands, coeff: dict) -> SoilParameter:
    """Predict Soil Organic Carbon (%) using spectral regression"""
    c = coeff["soc_model"]
    value = (
        c["B11_coeff"] * bands.B11
        + c["B12_coeff"] * bands.B12
        + c["BSI_coeff"] * indices.BSI
        + c["SWIR_ratio_coeff"] * indices.SWIR_ratio
        + c["NDVI_coeff"] * indices.NDVI
        + c["intercept"]
    )
    # Clamp to physically realistic range (0.1% – 6%)
    value = max(0.1, min(6.0, value))
    level_en, level_bn, icon = _classify(value, c["thresholds"])

    # Confidence based on NDVI — low vegetation = better soil signal
    confidence = "HIGH" if indices.NDVI < 0.4 else ("MEDIUM" if indices.NDVI < 0.7 else "LOW")

    return SoilParameter(
        value=round(value, 2),
        unit="%",
        level=level_en,
        level_bn=level_bn,
        icon=icon,
        confidence=confidence,
    )


def predict_nitrogen(soc: float, indices: SpectralIndices, coeff: dict) -> SoilParameter:
    """Predict Nitrogen level — tightly correlated with SOC + NDVI"""
    c = coeff["nitrogen_model"]
    value = (
        c["SOC_coeff"] * soc
        + c["NDVI_coeff"] * indices.NDVI
        + c["intercept"]
    )
    value = max(0.01, min(0.5, value))
    level_en, level_bn, icon = _classify(value, c["thresholds"])

    return SoilParameter(
        value=round(value, 3),
        unit="% total N",
        level=level_en,
        level_bn=level_bn,
        icon=icon,
        confidence="MEDIUM",
    )


def predict_moisture_stress(indices: SpectralIndices, bands: SentinelBands, coeff: dict) -> SoilParameter:
    """Predict moisture stress index (0 = no stress, 1 = severe)"""
    c = coeff["moisture_model"]
    value = (
        c["SWIR_ratio_coeff"] * indices.SWIR_ratio
        + c["NDVI_coeff"] * indices.NDVI
        + c["B11_coeff"] * bands.B11
        + c["intercept"]
    )
    value = max(0.0, min(1.0, value))
    level_en, level_bn, icon = _classify(value, c["thresholds"])

    return SoilParameter(
        value=round(value, 3),
        unit="index (0–1)",
        level=level_en,
        level_bn=level_bn,
        icon=icon,
        confidence="HIGH",
    )


def predict_waterlogging(indices: SpectralIndices, bands: SentinelBands, coeff: dict) -> SoilParameter:
    """Predict waterlogging risk probability (0–1)"""
    c = coeff["waterlogging_model"]
    value = (
        c["B8_coeff"] * bands.B8
        + c["NDWI_coeff"] * indices.NDWI
        + c["elevation_proxy_coeff"] * indices.BSI
        + c["intercept"]
    )
    # Sigmoid to keep in [0, 1]
    value = 1 / (1 + math.exp(-4 * (value - 0.5)))
    level_en, level_bn, icon = _classify(value, c["thresholds"])

    return SoilParameter(
        value=round(value, 3),
        unit="probability (0–1)",
        level=level_en,
        level_bn=level_bn,
        icon=icon,
        confidence="MEDIUM",
    )


def _compute_overall_health(soc: SoilParameter, nitrogen: SoilParameter, waterlogging: SoilParameter) -> tuple[str, str]:
    """Compute overall soil health score"""
    score = 0
    if soc.level == "HIGH":
        score += 3
    elif soc.level == "MEDIUM":
        score += 2
    else:
        score += 0

    if nitrogen.level == "ADEQUATE":
        score += 2
    elif nitrogen.level == "LOW":
        score += 1

    if waterlogging.level == "LOW RISK":
        score += 2
    elif waterlogging.level == "MEDIUM RISK":
        score += 1

    if score >= 6:
        return "GOOD", "ভালো"
    elif score >= 3:
        return "MODERATE", "মাঝারি"
    else:
        return "DEGRADED", "দুর্বল"


def _estimate_fertilizer_savings(soc: SoilParameter, crop: str = "boro_rice") -> dict:
    """Estimate fertilizer savings vs. common farmer practice (৳)"""
    savings = {}

    if crop == "boro_rice":
        # Common practice: 260 kg Urea/bigha; recommendation based on SOC
        if soc.level == "LOW":
            recommended_urea = 180
        elif soc.level == "MEDIUM":
            recommended_urea = 150
        else:
            recommended_urea = 130

        common_urea = 260
        urea_saved_kg = common_urea - recommended_urea
        urea_price_per_kg = 21  # ৳/kg (2024 subsidized rate)
        urea_saving_bdt = urea_saved_kg * urea_price_per_kg

        savings = {
            "crop": "Boro Rice",
            "crop_bn": "বোরো ধান",
            "recommended_urea_kg": recommended_urea,
            "common_urea_kg": common_urea,
            "urea_saved_kg": urea_saved_kg,
            "saving_bdt": urea_saving_bdt,
            "saving_formatted": f"৳{urea_saving_bdt:,}",
        }

    return savings


# ─── Main Prediction Orchestrator ─────────────────────────────────────────

def predict_soil_health(bands: SentinelBands, coefficients_path: str, crop: str = "boro_rice") -> SoilPrediction:
    """
    Main entry point: compute spectral indices and predict all soil parameters.
    """
    # Load coefficients
    with open(coefficients_path, "r", encoding="utf-8") as f:
        coeff = json.load(f)

    # Step 1: Compute indices
    indices = compute_spectral_indices(bands)
    logger.info(f"Spectral indices: NDVI={indices.NDVI:.3f}, BSI={indices.BSI:.3f}, SWIR_ratio={indices.SWIR_ratio:.3f}")

    # Step 2: Predict each parameter
    soc = predict_soc(indices, bands, coeff)
    nitrogen = predict_nitrogen(soc.value, indices, coeff)
    moisture = predict_moisture_stress(indices, bands, coeff)
    waterlogging = predict_waterlogging(indices, bands, coeff)

    logger.info(f"SOC: {soc.value}% ({soc.level}) | N: {nitrogen.level} | Moisture: {moisture.level} | Waterlog: {waterlogging.level}")

    # Step 3: Overall health + savings
    overall_en, overall_bn = _compute_overall_health(soc, nitrogen, waterlogging)
    savings = _estimate_fertilizer_savings(soc, crop)

    return SoilPrediction(
        soc=soc,
        nitrogen=nitrogen,
        moisture_stress=moisture,
        waterlogging_risk=waterlogging,
        indices=indices,
        overall_health=overall_en,
        overall_health_bn=overall_bn,
        savings_estimate=savings,
    )
