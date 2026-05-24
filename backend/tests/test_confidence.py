"""
Unit tests for the location confidence indicator in build_bangla_report.

Tests all 5 scenarios:
1. Live data — no confidence indicator
2. Demo data, distance=0 — no confidence indicator
3. <10km — High Confidence (🟢)
4. <50km — Medium Confidence (🟡)
5. <100km — Low Confidence (🟠)
6. >=100km — Very Low Confidence (🔴)
"""

import sys
import os

# Ensure the test can find the backend package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.response_builder import build_bangla_report
from backend.ml_module import SoilPrediction, SoilParameter, SpectralIndices
from backend.rag_module import FertilizerRecommendation


def make_mock_prediction() -> SoilPrediction:
    """Create a minimal SoilPrediction object with dummy data."""
    return SoilPrediction(
        soc=SoilParameter(
            value=1.2, unit="%", level="MODERATE", level_bn="মাঝারি",
            icon="🌿", confidence="medium",
        ),
        nitrogen=SoilParameter(
            value=30.0, unit="kg/ha", level="LOW", level_bn="নিম্ন",
            icon="🌾", confidence="high",
        ),
        moisture_stress=SoilParameter(
            value=0.4, unit="index", level="MODERATE", level_bn="মাঝারি",
            icon="💧", confidence="medium",
        ),
        waterlogging_risk=SoilParameter(
            value=0.2, unit="index", level="LOW", level_bn="কম",
            icon="🌊", confidence="high",
        ),
        indices=SpectralIndices(NDVI=0.65, BSI=0.12, SWIR_ratio=0.45, NDWI=0.18),
        overall_health="MODERATE",
        overall_health_bn="মাঝারি",
        savings_estimate={},
    )


def make_mock_recommendation() -> FertilizerRecommendation:
    """Create a minimal FertilizerRecommendation object with dummy data."""
    return FertilizerRecommendation(
        crop="boro_rice",
        crop_bn="বোরো ধান",
        season="বোরো",
        urea_kg=120,
        tsp_kg=80,
        mop_kg=60,
        zinc_sulfate_kg=5.0,
        other_nutrients=[],
        application_schedule=[
            "ইউরিয়া: ৩ ভাগে প্রয়োগ করুন",
            "TSP: শেষ চাষের সময় প্রয়োগ করুন",
        ],
        special_notes=["জিংক সালফেট ব্যবহার অত্যন্ত গুরুত্বপূর্ণ"],
        source="SRDI & BARC",
        query_matched="boro_rice_general",
        generated_by="keyword_match",
    )


def test_live_data_shows_no_confidence():
    """Live satellite data should not show any confidence indicator."""
    bangla, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.81,
        lon=90.41,
        acquisition_date="2025-05-25",
        data_source="gee_live",
        nearest_demo_dist_km=0.0,
    )
    # Should NOT contain confidence emojis or keywords
    assert "🟢" not in bangla and "🟡" not in bangla and "🟠" not in bangla and "🔴" not in bangla, "Live data should not show confidence emojis"
    assert "Confidence" not in english, "Live data should not show English confidence"
    # But should still contain the data source
    assert "লাইভ স্যাটেলাইট" in bangla, "Live data should label as live satellite"


def test_demo_zero_distance_shows_no_confidence():
    """Demo data with distance=0 should not show confidence indicator."""
    bangla, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.81,
        lon=90.41,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=0.0,
    )
    assert "🟢" not in bangla and "🟡" not in bangla and "🟠" not in bangla and "🔴" not in bangla, "Distance 0 should not show confidence emojis"
    assert "Confidence" not in english, "Distance 0 should not show English confidence"


def test_high_confidence_under_10km():
    """Distance < 10km should show High Confidence (🟢)."""
    bangla, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=24.85,
        lon=89.37,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=3.5,
    )
    assert "নির্ভরযোগ্য" in bangla, "High confidence should show in Bangla"
    assert "অত্যন্ত" in bangla, "High confidence Bangla mentions 'অত্যন্ত'"
    assert "High Confidence" in english, "High confidence should show in English"
    assert "🟢" in english, "High confidence should show green dot"


def test_medium_confidence_under_50km():
    """Distance < 50km should show Medium Confidence (🟡)."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=24.50,
        lon=89.00,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=25.0,
    )
    assert "Medium Confidence" in english, "Medium confidence should show in English"
    assert "🟡" in english, "Medium confidence should show yellow dot"
    assert "25" in english, "Should mention the distance in km"


def test_medium_confidence_edge_499km():
    """Distance exactly 49.9km should still be Medium Confidence."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=24.37,
        lon=89.00,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=49.9,
    )
    assert "Medium Confidence" in english, "49.9km should be Medium"
    assert "~50" in english, "Should round to 50km"


def test_low_confidence_under_100km():
    """Distance < 100km should show Low Confidence (🟠)."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.50,
        lon=89.50,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=75.0,
    )
    assert "Low Confidence" in english, "Low confidence should show in English"
    assert "🟠" in english, "Low confidence should show orange dot"
    assert "75" in english, "Should mention the distance in km"


def test_low_confidence_boundary_50km():
    """Distance exactly 50.0km should be Low Confidence (boundary)."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.50,
        lon=89.50,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=50.0,
    )
    assert "Low Confidence" in english, "50.0km should be Low"
    assert "🟠" in english, "50.0km should show orange dot"


def test_low_confidence_edge_999km():
    """Distance exactly 99.9km should still be Low Confidence."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.50,
        lon=89.50,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=99.9,
    )
    assert "Low Confidence" in english, "99.9km should be Low"


def test_very_low_confidence_over_100km():
    """Distance >= 100km should show Very Low Confidence (🔴)."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=22.00,
        lon=92.00,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=150.0,
    )
    assert "Very Low Confidence" in english, "150km should be Very Low"
    assert "🔴" in english, "Very Low should show red dot"
    assert "Indicative only" in english, "Should mention 'indicative only'"


def test_very_low_confidence_boundary_100km():
    """Distance exactly 100.0km should be Very Low Confidence (boundary)."""
    _, english = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=22.00,
        lon=92.00,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=100.0,
    )
    assert "Very Low Confidence" in english, "100.0km should be Very Low"
    assert "🔴" in english, "100.0km should show red dot"


def test_confidence_appears_after_coordinates():
    """Confidence line should appear between coordinates and the divider."""
    bangla, _ = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.81,
        lon=90.41,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=25.0,
    )
    # Coordinates come before confidence, soil health section comes after
    coord_pos = bangla.find("স্থানাঙ্ক")
    conf_pos = bangla.find("নির্ভরযোগ্য")
    health_pos = bangla.find("স্বাস্থ্য রিপোর্ট")
    assert coord_pos < conf_pos < health_pos, (
        f"Expected: Coordinates ({coord_pos}) < Confidence ({conf_pos}) "
        f"< Soil Health ({health_pos})"
    )


def test_bangla_numerals_in_confidence():
    """Bangla confidence text should use Bangla numerals for distances."""
    bangla, _ = build_bangla_report(
        prediction=make_mock_prediction(),
        recommendation=make_mock_recommendation(),
        district_name_bn="টেস্ট",
        district_code="TST",
        lat=23.81,
        lon=90.41,
        acquisition_date="2025-05-25",
        data_source="gee_demo",
        nearest_demo_dist_km=25.0,
    )
    # Distance 25 in Bangla numerals is ২৫
    # Note: "25" can appear elsewhere in the report (e.g. coordinates),
    # so we verify Bangla numerals ARE used instead of asserting "25" is absent.
    assert "২৫" in bangla, "Bangla confidence should use Bangla numerals"
    assert "~25" not in bangla, "Bangla confidence should NOT use Western km format"
