"""
MaatiGyan — RAG Module
Retrieves SRDI/BARC fertilizer recommendations using Qdrant + Groq + LlamaIndex.

DEMO MODE: Uses simple keyword matching if Groq API key not configured.
LIVE MODE: Full semantic vector search + Llama 3.1 8B generation via Groq.
"""
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FertilizerRecommendation:
    """Structured fertilizer recommendation output"""
    crop: str
    crop_bn: str
    season: str
    urea_kg: int
    tsp_kg: int
    mop_kg: int
    zinc_sulfate_kg: float
    other_nutrients: list[dict]
    application_schedule: list[str]
    special_notes: list[str]
    source: str
    query_matched: str
    generated_by: str  # "groq_rag" | "keyword_match"


# ─── Keyword-Based Fallback Engine ──────────────────────────────────────────

KEYWORD_RECOMMENDATIONS = {
    "boro_rice_low": FertilizerRecommendation(
        crop="Boro Rice", crop_bn="বোরো ধান",
        season="Rabi (নভেম্বর–মার্চ)",
        urea_kg=180, tsp_kg=55, mop_kg=40, zinc_sulfate_kg=2.0,
        other_nutrients=[{"name": "Gypsum", "amount": "15 kg/bigha", "condition": "if pH < 5.5"}],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 50% + জিংক সালফেট 100%",
            "১ম কিস্তি (১৫-২০ দিন পর): ইউরিয়া ৪০%",
            "২য় কিস্তি (৩০-৩৫ দিন পর): ইউরিয়া ৬০% + MoP ৫০%",
        ],
        special_notes=[
            "একসাথে সব ইউরিয়া দেবেন না — ৩ কিস্তিতে দিন (৩৫% সাশ্রয়)",
            "জিংকের অভাবে নিচের পাতায় বাদামি দাগ দেখা যায়",
            "জলাবদ্ধতায় MoP দিতে দেরি করুন",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 14",
        query_matched="boro_rice + low_soc",
        generated_by="keyword_match",
    ),
    "boro_rice_medium": FertilizerRecommendation(
        crop="Boro Rice", crop_bn="বোরো ধান",
        season="Rabi (নভেম্বর–মার্চ)",
        urea_kg=150, tsp_kg=45, mop_kg=35, zinc_sulfate_kg=1.5,
        other_nutrients=[{"name": "Borax", "amount": "1 kg/bigha", "condition": "if boron deficiency suspected"}],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 50% + জিংক সালফেট 100%",
            "১ম কিস্তি (১৫-২০ দিন পর): ইউরিয়া ৪০%",
            "২য় কিস্তি (৩০-৩৫ দিন পর): ইউরিয়া ৬০% + MoP ৫০%",
        ],
        special_notes=[
            "মাঝারি জৈব কার্বনের মাটি নাইট্রোজেন ধরে রাখে ভালো",
            "pH ৫.৫–৭.০ হলে জিপসামের দরকার নেই",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 15",
        query_matched="boro_rice + medium_soc",
        generated_by="keyword_match",
    ),
    "boro_rice_high": FertilizerRecommendation(
        crop="Boro Rice", crop_bn="বোরো ধান",
        season="Rabi (নভেম্বর–মার্চ)",
        urea_kg=130, tsp_kg=38, mop_kg=30, zinc_sulfate_kg=1.0,
        other_nutrients=[],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 50%",
            "১ম কিস্তি (১৫-২০ দিন পর): ইউরিয়া ৪০%",
            "২য় কিস্তি (৩০-৩৫ দিন পর): ইউরিয়া ৬০% + MoP ৫০%",
        ],
        special_notes=[
            "আপনার মাটিতে জৈব পদার্থ ভালো — রাসায়নিক সার কম লাগবে",
            "সবুজ সার (ঢেঞ্চা) দিলে আরও কমানো সম্ভব",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 15",
        query_matched="boro_rice + high_soc",
        generated_by="keyword_match",
    ),
    "aman_rice_low": FertilizerRecommendation(
        crop="Transplant Aman Rice", crop_bn="রোপা আমন ধান",
        season="Kharif-2 (জুন–নভেম্বর)",
        urea_kg=130, tsp_kg=40, mop_kg=30, zinc_sulfate_kg=2.0,
        other_nutrients=[],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 50% + জিংক সালফেট 100%",
            "১ম কিস্তি (১৫ দিন পর): ইউরিয়া ৪০%",
            "২য় কিস্তি (৩৫ দিন পর): ইউরিয়া ৬০% + MoP ৫০%",
        ],
        special_notes=[
            "৩ ইঞ্চির বেশি পানি থাকলে ইউরিয়া দেবেন না",
            "ঢেঞ্চা সবুজ সার দিলে নাইট্রোজেনের চাহিদা কমবে",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 8",
        query_matched="aman_rice + low_soc",
        generated_by="keyword_match",
    ),
    "wheat_low": FertilizerRecommendation(
        crop="Wheat", crop_bn="গম",
        season="Rabi (নভেম্বর–ফেব্রুয়ারি)",
        urea_kg=155, tsp_kg=50, mop_kg=32, zinc_sulfate_kg=1.0,
        other_nutrients=[{"name": "Gypsum", "amount": "20 kg/bigha"}],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 100% + জিপসাম 100% + জিংক 100%",
            "১ম কিস্তি (Crown root initiation): ইউরিয়া ৫০%",
            "২য় কিস্তি (Booting stage): ইউরিয়া ৫০%",
        ],
        special_notes=[
            "গম জলাবদ্ধতায় মরে যায় — নিষ্কাশন নিশ্চিত করুন",
            "বারিন্দ অঞ্চলে আগের বোরো ফসলের অবশিষ্ট ফসফেট কাজে লাগে",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 22",
        query_matched="wheat + low_soc",
        generated_by="keyword_match",
    ),
    "mustard_any": FertilizerRecommendation(
        crop="Mustard", crop_bn="সরিষা",
        season="Rabi (অক্টোবর–জানুয়ারি)",
        urea_kg=120, tsp_kg=55, mop_kg=35, zinc_sulfate_kg=0.5,
        other_nutrients=[
            {"name": "Gypsum", "amount": "25 kg/bigha", "condition": "CRITICAL — সরিষায় সালফার আবশ্যক"},
            {"name": "Borax", "amount": "2 kg/bigha", "condition": "CRITICAL — hollow stem রোধে"},
        ],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 100% + জিপসাম 100% + বোরন 100%",
            "১ম কিস্তি (২০ দিন পর): ইউরিয়া ৫০%",
            "২য় কিস্তি (ফুল আসার আগে): ইউরিয়া ৫০%",
        ],
        special_notes=[
            "সরিষায় সালফার ও বোরন সবচেয়ে গুরুত্বপূর্ণ — বাদ দেবেন না",
            "Hollow stem মানে বোরনের অভাব",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 28",
        query_matched="mustard + any_soc",
        generated_by="keyword_match",
    ),
    "potato_any": FertilizerRecommendation(
        crop="Potato", crop_bn="আলু",
        season="Rabi (অক্টোবর–ফেব্রুয়ারি)",
        urea_kg=165, tsp_kg=80, mop_kg=75, zinc_sulfate_kg=1.0,
        other_nutrients=[
            {"name": "Gypsum", "amount": "20 kg/bigha"},
            {"name": "Magnesium Sulfate", "amount": "5 kg/bigha"},
        ],
        application_schedule=[
            "বপনের সময়: TSP 100% + MoP 50% + জিপসাম 100% + MgSO4 100%",
            "১ম কিস্তি (Stolon initiation): ইউরিয়া ৫০% + MoP ৫০%",
            "২য় কিস্তি (Tuber bulking): ইউরিয়া ৫০%",
        ],
        special_notes=[
            "গোবর সার ২-৩ টন/বিঘা দিলে ফলন ও মাটির গুণ উভয় ভালো হয়",
            "Ridge planting করুন — ২৪ ঘণ্টা জলাবদ্ধতায় আলু নষ্ট হয়",
            "ব্যাকটেরিয়াল রট রোধে certified seed ব্যবহার করুন",
        ],
        source="BARC Fertilizer Recommendation Guide 2023, Table 35",
        query_matched="potato + any_soc",
        generated_by="keyword_match",
    ),
}

CROP_ALIASES = {
    "rice": "boro_rice", "ধান": "boro_rice", "বোরো": "boro_rice",
    "boro": "boro_rice", "boro_rice": "boro_rice",
    "aman": "aman_rice", "আমন": "aman_rice",
    "wheat": "wheat", "গম": "wheat",
    "mustard": "mustard", "সরিষা": "mustard",
    "potato": "potato", "আলু": "potato",
}


def _keyword_recommend(
    soc_level: str,  # "LOW" | "MEDIUM" | "HIGH"
    crop: str = "boro_rice",
) -> FertilizerRecommendation:
    """Simple keyword matching fallback recommendation"""
    # Normalise crop name
    crop_key = CROP_ALIASES.get(crop.lower(), "boro_rice")
    soc_suffix = soc_level.lower()

    # Try specific key first, then any
    key = f"{crop_key}_{soc_suffix}"
    if key not in KEYWORD_RECOMMENDATIONS:
        key = f"{crop_key}_any"
    if key not in KEYWORD_RECOMMENDATIONS:
        key = "boro_rice_low"  # Ultimate fallback

    return KEYWORD_RECOMMENDATIONS[key]


# ─── Groq RAG Engine ─────────────────────────────────────────────────────────

_rag_index = None  # Module-level cache


def _build_rag_index(corpus_path: str, qdrant_url: str, qdrant_api_key: str, collection: str):
    """Build or load Qdrant + LlamaIndex RAG index from SRDI corpus"""
    global _rag_index
    if _rag_index is not None:
        return _rag_index

    try:
        from llama_index.core import VectorStoreIndex, StorageContext, Settings, SimpleDirectoryReader
        from llama_index.llms.groq import Groq
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        import qdrant_client

        logger.info("Building RAG index from SRDI corpus...")

        # Configure embedding model (local, no API key needed)
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")
        Settings.embed_model = embed_model
        Settings.chunk_size = 512

        # Configure Qdrant
        if qdrant_url == ":memory:":
            qclient = qdrant_client.QdrantClient(location=":memory:")
        else:
            qclient = qdrant_client.QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key or None,
            )

        vector_store = QdrantVectorStore(client=qclient, collection_name=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Load SRDI corpus
        corpus_dir = os.path.dirname(corpus_path)
        documents = SimpleDirectoryReader(corpus_dir, filename_as_id=True).load_data()
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        _rag_index = index
        logger.info("RAG index built successfully")
        return index

    except Exception as e:
        logger.error(f"Failed to build RAG index: {e}")
        return None


def get_fertilizer_recommendation(
    soc_level: str,
    nitrogen_level: str,
    moisture_level: str,
    crop: str = "boro_rice",
    district: str = "General",
    groq_api_key: str = "",
    corpus_path: str = "",
    qdrant_url: str = ":memory:",
    qdrant_api_key: str = "",
    qdrant_collection: str = "srdi_recommendations",
) -> FertilizerRecommendation:
    """
    Main entry point: Get crop-specific fertilizer recommendation.
    - If Groq API key available: uses full RAG (Qdrant + Groq)
    - Otherwise: uses keyword matching fallback
    """
    # Try RAG first
    if groq_api_key and corpus_path:
        try:
            rec = _get_rag_recommendation(
                soc_level, nitrogen_level, moisture_level, crop, district,
                groq_api_key, corpus_path, qdrant_url, qdrant_api_key, qdrant_collection,
            )
            if rec:
                return rec
        except Exception as e:
            logger.warning(f"RAG failed, falling back to keyword match: {e}")

    # Fallback: keyword matching
    logger.info("Using keyword-match recommendation engine")
    return _keyword_recommend(soc_level, crop)


def _get_rag_recommendation(
    soc_level, nitrogen_level, moisture_level, crop, district,
    groq_api_key, corpus_path, qdrant_url, qdrant_api_key, qdrant_collection,
) -> Optional[FertilizerRecommendation]:
    """Full RAG-based recommendation using Groq + Qdrant"""
    from llama_index.llms.groq import Groq
    from llama_index.core import Settings

    index = _build_rag_index(corpus_path, qdrant_url, qdrant_api_key, qdrant_collection)
    if index is None:
        return None

    llm = Groq(model="llama-3.1-8b-instant", api_key=groq_api_key)
    Settings.llm = llm

    query = (
        f"Fertilizer recommendation for {crop} in {district}. "
        f"Soil conditions: SOC={soc_level}, Nitrogen={nitrogen_level}, "
        f"Moisture Stress={moisture_level}. "
        f"Provide specific kg/bigha rates for Urea, TSP, MoP, Zinc Sulfate."
    )

    query_engine = index.as_query_engine(similarity_top_k=3)
    response = query_engine.query(query)
    raw_text = str(response)
    logger.info(f"RAG response: {raw_text[:200]}...")

    # Parse structured values from LLM response
    # Extract kg values using regex
    def extract_kg(pattern: str, text: str, default: int) -> int:
        m = re.search(pattern, text, re.IGNORECASE)
        return int(m.group(1)) if m else default

    base = _keyword_recommend(soc_level, crop)  # Use as structural template
    urea = extract_kg(r"[Uu]rea[:\s]+(\d+)\s*kg", raw_text, base.urea_kg)
    tsp = extract_kg(r"TSP[:\s]+(\d+)\s*kg", raw_text, base.tsp_kg)
    mop = extract_kg(r"MoP[:\s]+(\d+)\s*kg", raw_text, base.mop_kg)

    return FertilizerRecommendation(
        crop=base.crop,
        crop_bn=base.crop_bn,
        season=base.season,
        urea_kg=urea,
        tsp_kg=tsp,
        mop_kg=mop,
        zinc_sulfate_kg=base.zinc_sulfate_kg,
        other_nutrients=base.other_nutrients,
        application_schedule=base.application_schedule,
        special_notes=base.special_notes,
        source="BARC Fertilizer Recommendation Guide 2023 (via RAG)",
        query_matched=query,
        generated_by="groq_rag",
    )
