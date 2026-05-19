# TODO: Replace mock analysis with real
# PyTorch EfficientNetV2 model
# Model path: greencare-ai/models/
# Input: 6 images from different angles
# Output: 1 combined disease analysis result

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


async def analyze_images(
    image_paths: list[str],
) -> dict:
    """
    Analyzes 6 images of same zone
    from different angles and returns
    1 combined result.

    # TODO: Replace mock with real
    # PyTorch EfficientNetV2 model
    # when greencare-ai is ready
    """
    if len(image_paths) != 6:
        raise ValueError("analyze_images requires exactly 6 image paths")

    for path in image_paths:
        _ = path  # Placeholder until model consumes image input.

    # Simulate processing time
    # (remove when real model added)
    await asyncio.sleep(2)

    # Mock disease types with Korean
    # and English recommendations
    diseases = [
        {
            "type": "dollar_spot",
            "rec_en": "Apply fungicide within 48 hours. Reduce irrigation frequency.",
            "rec_ko": "48시간 내 살균제를 살포하세요. 관수 빈도를 줄이세요.",
        },
        {
            "type": "brown_patch",
            "rec_en": "Apply contact fungicide. Improve air circulation.",
            "rec_ko": "접촉성 살균제를 살포하세요. 통기성을 개선하세요.",
        },
        {
            "type": "pythium_blight",
            "rec_en": "Apply Pythium-specific fungicide immediately.",
            "rec_ko": "피시움 전용 살균제를 즉시 살포하세요.",
        },
        {
            "type": "fairy_ring",
            "rec_en": "Apply wetting agent and systemic fungicide.",
            "rec_ko": "습윤제와 침투성 살균제를 살포하세요.",
        },
        {
            "type": "anthracnose",
            "rec_en": "Reduce stress on turf. Apply fungicide.",
            "rec_ko": "잔디 스트레스를 줄이고 살균제를 살포하세요.",
        },
        {
            "type": "leaf_spot",
            "rec_en": "Apply preventive fungicide program.",
            "rec_ko": "예방적 살균제 프로그램을 적용하세요.",
        },
    ]

    # 60% chance disease found
    # 40% chance healthy
    disease_found = random.random() > 0.4

    if not disease_found:
        result = {
            "condition": "good",
            "disease_type": None,
            "confidence": round(random.uniform(0.90, 0.99), 2),
            "severity": None,
            "affected_area_percent": 0,
            "recommendation_en": (
                "Grass condition is good. Continue regular maintenance."
            ),
            "recommendation_ko": (
                "잔디 상태가 양호합니다. 정기적인 관리를 계속하세요."
            ),
            "model_version": "mock-1.0.0",
            "images_analyzed": len(image_paths),
        }
        logger.info(
            "AI mock analysis (6 images) condition=%s confidence=%s",
            result["condition"],
            result["confidence"],
        )
        return result

    disease = random.choice(diseases)
    severities = ["low", "moderate", "high", "critical"]
    severity = random.choice(severities)

    result = {
        "condition": "disease_found",
        "disease_type": disease["type"],
        "confidence": round(random.uniform(0.75, 0.97), 2),
        "severity": severity,
        "affected_area_percent": round(random.uniform(5, 45), 1),
        "recommendation_en": disease["rec_en"],
        "recommendation_ko": disease["rec_ko"],
        "model_version": "mock-1.0.0",
        "images_analyzed": len(image_paths),
    }
    logger.info(
        "AI mock analysis (6 images) condition=%s disease=%s confidence=%s severity=%s",
        result["condition"],
        result["disease_type"],
        result["confidence"],
        result["severity"],
    )
    return result


def get_disease_display_name(
    disease_type: str,
    language: str = "en",
) -> str:
    names = {
        "dollar_spot": {
            "en": "Dollar Spot",
            "ko": "달러 스팟",
        },
        "brown_patch": {
            "en": "Brown Patch",
            "ko": "브라운 패치",
        },
        "pythium_blight": {
            "en": "Pythium Blight",
            "ko": "피시움 블라이트",
        },
        "fairy_ring": {
            "en": "Fairy Ring",
            "ko": "페어리 링",
        },
        "anthracnose": {
            "en": "Anthracnose",
            "ko": "탄저병",
        },
        "leaf_spot": {
            "en": "Leaf Spot",
            "ko": "잎마름병",
        },
    }

    disease = names.get(disease_type, {})
    return disease.get(language, disease_type)
