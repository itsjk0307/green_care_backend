from __future__ import annotations

from typing import Any


def get_fixed_mock_scan_results() -> list[dict[str, Any]]:
    """Fixed mock AI results until the real drone model is ready."""
    return [
        {
            "hole_number": 3,
            "disease_type": "dollar_spot",
            "confidence": 0.87,
            "severity": "high",
            "affected_area_pct": 23.5,
            "bbox_x": 15.2,
            "bbox_y": 22.8,
            "bbox_width": 18.5,
            "bbox_height": 14.2,
            "recommendation_ko": (
                "Chlorothalonil 살균제를 2주 간격으로 살포하세요. 배수 개선도 필요합니다."
            ),
            "recommendation_en": (
                "Apply Chlorothalonil fungicide every 2 weeks. Improve drainage."
            ),
        },
        {
            "hole_number": 7,
            "disease_type": "brown_patch",
            "confidence": 0.64,
            "severity": "medium",
            "affected_area_pct": 11.0,
            "bbox_x": 45.0,
            "bbox_y": 58.3,
            "bbox_width": 12.0,
            "bbox_height": 9.5,
            "recommendation_ko": "질소 시비를 줄이고 통기작업을 실시하세요.",
            "recommendation_en": "Reduce nitrogen fertilization and perform aeration.",
        },
        {
            "hole_number": 1,
            "disease_type": "healthy",
            "confidence": 0.95,
            "severity": "low",
            "affected_area_pct": 0.0,
            "bbox_x": None,
            "bbox_y": None,
            "bbox_width": None,
            "bbox_height": None,
            "recommendation_ko": "현재 상태 양호. 정기 관리를 유지하세요.",
            "recommendation_en": "Current condition good. Maintain regular care.",
        },
        {
            "hole_number": 12,
            "disease_type": "pythium_blight",
            "confidence": 0.71,
            "severity": "high",
            "affected_area_pct": 8.3,
            "bbox_x": 62.1,
            "bbox_y": 31.5,
            "bbox_width": 9.8,
            "bbox_height": 7.4,
            "recommendation_ko": "즉시 Mefenoxam 살균제를 살포하세요. 과습 주의.",
            "recommendation_en": "Apply Mefenoxam fungicide immediately. Avoid overwatering.",
        },
        {
            "hole_number": 5,
            "disease_type": "healthy",
            "confidence": 0.91,
            "severity": "low",
            "affected_area_pct": 0.0,
            "bbox_x": None,
            "bbox_y": None,
            "bbox_width": None,
            "bbox_height": None,
            "recommendation_ko": "정상 상태. 계속 현재 관리 방식을 유지하세요.",
            "recommendation_en": "Healthy condition. Continue current management.",
        },
    ]
