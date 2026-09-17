"""Shared helpers for region normalization and stats, used by the ETL
script (scripts/build_aggregates.py) and the API layer (app/main.py).
"""
from __future__ import annotations

import math

# Canonical region id -> display names.
# id order/list confirmed against both source datasets during data
# exploration: exam files have 25 unique oblast values (24 oblasts + м.Київ),
# alert file has 25 unique oblast values (24 oblasts + Kyiv City) -- exact
# 1:1 correspondence, no fuzzy matching.
# "iso" is the ISO 3166-2:UA subdivision code, used to join against the
# frontend's oblast GeoJSON (geoBoundaries UKR ADM1, shapeISO property) --
# an exact code match, not name matching.
REGIONS = {
    "vinnytska": {"uk": "Вінницька область", "en": "Vinnytska oblast", "label": "Vinnytsia", "iso": "UA-05"},
    "volynska": {"uk": "Волинська область", "en": "Volynska oblast", "label": "Volyn", "iso": "UA-07"},
    "dnipropetrovska": {"uk": "Дніпропетровська область", "en": "Dnipropetrovska oblast", "label": "Dnipropetrovsk", "iso": "UA-12"},
    "donetska": {"uk": "Донецька область", "en": "Donetska oblast", "label": "Donetsk", "iso": "UA-14"},
    "zhytomyrska": {"uk": "Житомирська область", "en": "Zhytomyrska oblast", "label": "Zhytomyr", "iso": "UA-18"},
    "zakarpatska": {"uk": "Закарпатська область", "en": "Zakarpatska oblast", "label": "Zakarpattia", "iso": "UA-21"},
    "zaporizka": {"uk": "Запорізька область", "en": "Zaporizka oblast", "label": "Zaporizhzhia", "iso": "UA-23"},
    "ivano_frankivska": {"uk": "Івано-Франківська область", "en": "Ivano-Frankivska oblast", "label": "Ivano-Frankivsk", "iso": "UA-26"},
    "kyivska": {"uk": "Київська область", "en": "Kyivska oblast", "label": "Kyiv Oblast", "iso": "UA-32"},
    "kirovohradska": {"uk": "Кіровоградська область", "en": "Kirovohradska oblast", "label": "Kirovohrad", "iso": "UA-35"},
    "luhanska": {"uk": "Луганська область", "en": "Luhanska oblast", "label": "Luhansk", "iso": "UA-09"},
    "lvivska": {"uk": "Львівська область", "en": "Lvivska oblast", "label": "Lviv", "iso": "UA-46"},
    "mykolaivska": {"uk": "Миколаївська область", "en": "Mykolaivska oblast", "label": "Mykolaiv", "iso": "UA-48"},
    "odeska": {"uk": "Одеська область", "en": "Odeska oblast", "label": "Odesa", "iso": "UA-51"},
    "poltavska": {"uk": "Полтавська область", "en": "Poltavska oblast", "label": "Poltava", "iso": "UA-53"},
    "rivnenska": {"uk": "Рівненська область", "en": "Rivnenska oblast", "label": "Rivne", "iso": "UA-56"},
    "sumska": {"uk": "Сумська область", "en": "Sumska oblast", "label": "Sumy", "iso": "UA-59"},
    "ternopilska": {"uk": "Тернопільська область", "en": "Ternopilska oblast", "label": "Ternopil", "iso": "UA-61"},
    "kharkivska": {"uk": "Харківська область", "en": "Kharkivska oblast", "label": "Kharkiv", "iso": "UA-63"},
    "khersonska": {"uk": "Херсонська область", "en": "Khersonska oblast", "label": "Kherson", "iso": "UA-65"},
    "khmelnytska": {"uk": "Хмельницька область", "en": "Khmelnytska oblast", "label": "Khmelnytskyi", "iso": "UA-68"},
    "cherkaska": {"uk": "Черкаська область", "en": "Cherkaska oblast", "label": "Cherkasy", "iso": "UA-71"},
    "chernivetska": {"uk": "Чернівецька область", "en": "Chernivetska oblast", "label": "Chernivtsi", "iso": "UA-77"},
    "chernihivska": {"uk": "Чернігівська область", "en": "Chernihivska oblast", "label": "Chernihiv", "iso": "UA-74"},
    "kyiv_city": {"uk": "м.Київ", "en": "Kyiv City", "label": "Kyiv City", "iso": "UA-30"},
}

EXAM_REGION_TO_ID = {v["uk"]: k for k, v in REGIONS.items()}
ALERT_REGION_TO_ID = {v["en"]: k for k, v in REGIONS.items()}

# Values present in exam RegName columns that are not real regions and must
# be dropped (seen starting in the 2023 file).
EXAM_REGION_IGNORE = {"Інші країни", None, ""}


def normalize_score(raw: object) -> float | None:
    """Parse a exam Ball100-style score field.

    Source files use a comma decimal separator (e.g. "149,0") and encode
    missing values as either an empty string or the literal string "null".
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "null":
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def weighted_score_rollup(rows: list[dict]) -> dict | None:
    """Combine several {avg, min, max, count} score rows (e.g. across
    subjects or regions) into one, weighting the average by count."""
    total_count = sum(r["count"] for r in rows)
    if total_count == 0:
        return None
    weighted_avg = sum(r["avg"] * r["count"] for r in rows) / total_count
    return {
        "avg": round(weighted_avg, 2),
        "min": min(r["min"] for r in rows),
        "max": max(r["max"] for r in rows),
        "count": total_count,
    }


def pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation coefficient. Returns None if undefined
    (fewer than 2 points, or zero variance in either series)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return None
    return cov / denom
