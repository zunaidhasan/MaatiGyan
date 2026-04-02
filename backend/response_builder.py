"""
MaatiGyan — Bangla Report Builder + gTTS Voice Note Generator

Builds structured Bangla WhatsApp-formatted text reports and
generates Bangla audio voice notes via Google TTS.
"""
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .ml_module import SoilPrediction
from .rag_module import FertilizerRecommendation

logger = logging.getLogger(__name__)


@dataclass
class SoilReport:
    """Complete soil report ready for WhatsApp delivery"""
    text_report: str           # Full Bangla text (WhatsApp formatted)
    text_report_en: str        # English version
    summary_line: str          # One-line Bangla summary
    audio_path: Optional[str]  # Path to .mp3 voice note (if generated)
    report_id: str             # Unique ID for tracking


# ─── Bangla Numerals ─────────────────────────────────────────────────────────

_BANGLA_DIGITS = str.maketrans("0123456789.", "০১২৩৪৫৬৭৮৯.")

def to_bangla_num(value) -> str:
    return str(value).translate(_BANGLA_DIGITS)


def build_bangla_report(
    prediction: SoilPrediction,
    recommendation: FertilizerRecommendation,
    district_name_bn: str,
    district_code: str,
    lat: float,
    lon: float,
    acquisition_date: str,
    data_source: str,
    farmer_name: Optional[str] = None,
    land_area: float = 1.0,
) -> tuple[str, str]:
    """
    Build formatted Bangla + English soil reports.
    Returns (bangla_text, english_text)
    """
    soc = prediction.soc
    nit = prediction.nitrogen
    moist = prediction.moisture_stress
    wlog = prediction.waterlogging_risk
    savings = prediction.savings_estimate
    rec = recommendation

    divider = "━" * 22

    # ── Savings line ──
    if savings.get("urea_saved_kg", 0) > 0:
        savings_line_bn = (
            f"💰 সাশ্রয়: ইউরিয়া {to_bangla_num(savings['urea_saved_kg'])} কেজি কম = "
            f"*{savings['saving_formatted']}* বাঁচবে"
        )
        savings_line_en = (
            f"💰 Savings: Use {savings['urea_saved_kg']} kg less Urea = "
            f"Save {savings['saving_formatted']} per bigha"
        )
    else:
        savings_line_bn = ""
        savings_line_en = ""

    # ── Extra nutrients ──
    other_bn_lines = []
    other_en_lines = []
    for n in rec.other_nutrients:
        cond = f" ({n.get('condition', '')})" if n.get("condition") else ""
        other_en_lines.append(f"  • {n['name']}: {n['amount']}{cond}")
        other_bn_lines.append(f"  • {n['name']}: {n['amount']}{cond}")

    # ── Application schedule ──
    schedule_bn = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(rec.application_schedule)])

    # ── Special notes ──
    notes_bn = "\n".join([f"  ⚡ {n}" for n in rec.special_notes[:3]])

    # ── Source ──
    source_date = datetime.strptime(acquisition_date, "%Y-%m-%d").strftime("%d %b %Y") if acquisition_date else "সাম্প্রতিক"
    data_label = "লাইভ স্যাটেলাইট" if data_source == "gee_live" else "ডেমো ডেটা"

    # ═══ BANGLA REPORT ═══════════════════════════════════════
    greeting_bn = f"জনাব {farmer_name}, " if farmer_name else ""
    area_bn = f" ({to_bangla_num(land_area)} বিঘা)" if land_area > 1.0 else ""

    bangla = f"""🌱 *{greeting_bn}আপনার জমির রিপোর্ট*
_(মাটিজ্ঞান — স্যাটেলাইট মাটি বিশ্লেষণ)_

📍 *এলাকা:* {district_name_bn} | ব্লক: {district_code}
🛰️ *উপগ্রহ তথ্য:* {source_date} ({data_label})
🌍 *স্থানাঙ্ক:* {lat:.4f}°N, {lon:.4f}°E
{divider}
🧪 *মাটির স্বাস্থ্য রিপোর্ট*
{divider}
🌿 জৈব কার্বন (SOC): *{soc.icon} {soc.level_bn}* ({to_bangla_num(soc.value)}%)
🌾 নাইট্রোজেন: *{nit.icon} {nit.level_bn}*
💧 আর্দ্রতা চাপ: *{moist.icon} {moist.level_bn}*
🌊 জলাবদ্ধতা ঝুঁকি: *{wlog.icon} {wlog.level_bn}*
{divider}
📊 সার্বিক মাটির স্বাস্থ্য: *{prediction.overall_health_bn}*
{divider}
🌾 *{rec.season} সুপারিশ ({rec.crop_bn}){area_bn}*
{divider}
  • ইউরিয়া: *{to_bangla_num(round(rec.urea_kg * land_area, 1))} কেজি*
  • TSP: *{to_bangla_num(round(rec.tsp_kg * land_area, 1))} কেজি*
  • MoP: *{to_bangla_num(round(rec.mop_kg * land_area, 1))} কেজি*
  • জিংক সালফেট: *{to_bangla_num(round(rec.zinc_sulfate_kg * land_area, 1))} কেজি* ⚠️
{"".join(other_bn_lines)}
{divider}
📅 *প্রয়োগের সময়সূচি*
{schedule_bn}
{divider}
💡 *বিশেষ পরামর্শ*
{notes_bn}
{divider}
{savings_line_bn}
{divider}
📚 *সূত্র:* {rec.source}
🤖 _মাটিজ্ঞান AI — আপনার জমির নির্ভরযোগ্য সঙ্গী_
_SRDI · BARC · Sentinel-2 ESA Copernicus_"""

    # ═══ ENGLISH REPORT ══════════════════════════════════════
    greeting_en = f"Dear {farmer_name}, " if farmer_name else ""
    area_en = f" ({land_area} Bigha)" if land_area > 1.0 else ""

    english = f"""🌱 *{greeting_en}Field Health Report*
_(MaatiGyan — Satellite Soil Intelligence)_

📍 *Location:* {district_name_bn} | Block: {district_code}
🛰️ *Satellite Data:* {source_date} ({data_source})
🌍 *Coordinates:* {lat:.4f}°N, {lon:.4f}°E
{divider}
🧪 *SOIL HEALTH ANALYSIS*
{divider}
🌿 Soil Organic Carbon: *{soc.icon} {soc.level}* ({soc.value}%)
🌾 Nitrogen Level: *{nit.icon} {nit.level}*
💧 Moisture Stress: *{moist.icon} {moist.level}*
🌊 Waterlogging Risk: *{wlog.icon} {wlog.level}*
{divider}
📊 Overall Soil Health: *{prediction.overall_health}*
{divider}
🌾 *{rec.season} Recommendation ({rec.crop}){area_en}*
{divider}
  • Urea: *{round(rec.urea_kg * land_area, 1)} kg*
  • TSP: *{round(rec.tsp_kg * land_area, 1)} kg*
  • MoP: *{round(rec.mop_kg * land_area, 1)} kg*
  • Zinc Sulfate: *{round(rec.zinc_sulfate_kg * land_area, 1)} kg* ⚠️
{"".join(other_en_lines)}
{divider}
📅 *Application Schedule*
{schedule_bn}
{divider}
💡 *Special Notes*
{notes_bn}
{divider}
{savings_line_en}
{divider}
📚 *Source:* {rec.source}
🤖 _MaatiGyan AI — Precise Satellite Soil Testing_
_SRDI · BARC · Sentinel-2 ESA Copernicus_"""

    return bangla.strip(), english.strip()


# ─── Voice Note Generator ────────────────────────────────────────────────────

def generate_voice_note(
    prediction: SoilPrediction,
    recommendation: FertilizerRecommendation,
    district_name_bn: str,
    audio_dir: str,
    lang: str = "bn",
) -> Optional[str]:
    """
    Generate a Bangla voice note summarizing the soil report.
    Returns the path to the .mp3 file, or None if gTTS fails.
    """
    try:
        from gtts import gTTS

        os.makedirs(audio_dir, exist_ok=True)

        soc = prediction.soc
        nit = prediction.nitrogen
        rec = recommendation
        savings = prediction.savings_estimate

        savings_text = ""
        if savings.get("urea_saved_kg", 0) > 0:
            savings_text = (
                f"এই সুপারিশ মেনে চললে প্রতি বিঘায় {savings['saving_formatted']} বাঁচাতে পারবেন। "
            )

        # Bangla TTS script — concise and conversational
        script = (
            f"আপনার জমির মাটি পরীক্ষার ফলাফল। "
            f"এলাকা: {district_name_bn}। "
            f"আপনার মাটির জৈব কার্বন {soc.level_bn}। "
            f"নাইট্রোজেন {nit.level_bn}। "
            f"মাটির সার্বিক স্বাস্থ্য {prediction.overall_health_bn}। "
            f"{rec.season} মৌসুমে {rec.crop_bn} চাষের জন্য সুপারিশ: "
            f"ইউরিয়া {rec.urea_kg} কেজি প্রতি বিঘা, "
            f"টিএসপি {rec.tsp_kg} কেজি, "
            f"এমওপি {rec.mop_kg} কেজি, "
            f"এবং জিংক সালফেট {rec.zinc_sulfate_kg} কেজি। "
            f"{savings_text}"
            f"বিস্তারিত জানতে টেক্সট বার্তাটি দেখুন। "
            f"মাটিজ্ঞান — আপনার জমির বিশ্বস্ত সঙ্গী।"
        )

        # Cache audio by content hash to avoid regenerating identical reports
        content_hash = hashlib.md5(script.encode()).hexdigest()[:8]
        audio_path = os.path.join(audio_dir, f"report_{content_hash}.mp3")

        if not os.path.exists(audio_path):
            tts = gTTS(text=script, lang=lang, slow=False)
            tts.save(audio_path)
            logger.info(f"Voice note saved: {audio_path}")
        else:
            logger.info(f"Using cached voice note: {audio_path}")

        return audio_path

    except ImportError:
        logger.warning("gTTS not installed. Run: pip install gTTS")
        return None
    except Exception as e:
        logger.error(f"Voice note generation failed: {e}")
        return None


# ─── Main Report Builder ──────────────────────────────────────────────────────

def build_soil_report(
    prediction: SoilPrediction,
    recommendation: FertilizerRecommendation,
    district_name_bn: str,
    district_code: str,
    lat: float,
    lon: float,
    acquisition_date: str,
    data_source: str,
    audio_dir: str,
    generate_audio: bool = True,
    language: str = "bn",  # "bn" = Bangla, "en" = English
    farmer_name: Optional[str] = None,
    land_area: float = 1.0,
) -> SoilReport:
    """Orchestrates report text building + voice note generation"""

    bangla_text, english_text = build_bangla_report(
        prediction, recommendation,
        district_name_bn, district_code,
        lat, lon, acquisition_date, data_source,
        farmer_name=farmer_name,
        land_area=land_area,
    )

    # Select report text based on language preference
    primary_text = bangla_text if language == "bn" else english_text

    # Summary line (one-liner for notifications)
    summary = (
        f"মাটি: {prediction.overall_health_bn} | SOC {prediction.soc.level_bn} "
        f"({prediction.soc.value}%) | {recommendation.crop_bn}: "
        f"ইউরিয়া {recommendation.urea_kg} কেজি/বিঘা"
    )

    # Generate voice note
    audio_path = None
    if generate_audio:
        audio_path = generate_voice_note(
            prediction, recommendation,
            district_name_bn, audio_dir,
            lang="bn",
        )

    # Unique report ID
    report_id = hashlib.md5(
        f"{lat:.4f}{lon:.4f}{acquisition_date}".encode()
    ).hexdigest()[:12]

    return SoilReport(
        text_report=primary_text,
        text_report_en=english_text,
        summary_line=summary,
        audio_path=audio_path,
        report_id=report_id,
    )
