from __future__ import annotations

import json
import re
from typing import Any


def extract_hole_number(
    work_types: list[str],
    notes: str | None = None,
    zone_coordinates: list[dict[str, Any]] | None = None,
) -> int | None:
    """Extract hole number 1-18 from work_types metadata, notes JSON, or zone_coordinates."""
    for work_type in work_types:
        match = re.match(r"^hole_(\d+)$", str(work_type).strip(), re.IGNORECASE)
        if match:
            hole = int(match.group(1))
            if 1 <= hole <= 18:
                return hole

    if notes:
        try:
            parsed = json.loads(notes)
            if isinstance(parsed, dict) and "hole_number" in parsed:
                hole = int(parsed["hole_number"])
                if 1 <= hole <= 18:
                    return hole
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    if zone_coordinates:
        for zone in zone_coordinates:
            if isinstance(zone, dict) and "hole_number" in zone:
                try:
                    hole = int(zone["hole_number"])
                    if 1 <= hole <= 18:
                        return hole
                except (TypeError, ValueError):
                    continue

    return None
