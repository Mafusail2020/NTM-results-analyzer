import json
import os
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.aggregation import pearson_correlation, weighted_score_rollup
from app.schemas import (
    AlertsDailyResponse,
    AlertsResponse,
    CorrelationResponse,
    RegionsResponse,
    ScoresByRegionResponse,
    ScoresBySexResponse,
    ScoresResponse,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "aggregates.json"

app = FastAPI(title="Ukraine Exam Scores & Wartime Disruption API")

DEFAULT_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
]
# Comma-separated extra allowed origins (e.g. the deployed Vercel URL),
# on top of the local dev ports above.
EXTRA_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_ORIGINS + EXTRA_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_data: dict = {}


@app.on_event("startup")
def load_data() -> None:
    if not DATA_PATH.exists():
        raise RuntimeError(
            f"Processed data not found at {DATA_PATH}. "
            "Run `python scripts/build_aggregates.py` first."
        )
    with open(DATA_PATH, encoding="utf-8") as f:
        _data.update(json.load(f))


def region_ids() -> set[str]:
    return {r["id"] for r in _data["meta"]["regions"]}


@app.get("/api/regions", response_model=RegionsResponse)
def get_regions():
    return {
        "regions": _data["meta"]["regions"],
        "subjects": _data["meta"]["subjects"],
        "years": _data["meta"]["years"],
        "notes": _data["meta"]["notes"],
    }


@app.get("/api/scores", response_model=ScoresResponse)
def get_scores(
    region: str | None = Query(None, description="Region id, or omitted/'all' for national aggregate"),
    year: int | None = Query(None),
    subject: str | None = Query(None, description="Subject id; omitted = all subjects combined"),
):
    if region and region != "all" and region not in region_ids():
        raise HTTPException(404, f"Unknown region '{region}'")

    rows = _data["scores"]
    if year is not None:
        rows = [r for r in rows if r["year"] == year]
    if subject is not None:
        rows = [r for r in rows if r["subject"] == subject]
    if region and region != "all":
        rows = [r for r in rows if r["region"] == region]

    student_rows = _data["student_counts"]
    if year is not None:
        student_rows = [r for r in student_rows if r["year"] == year]
    if region and region != "all":
        student_rows = [r for r in student_rows if r["region"] == region]

    # Group remaining rows by year (region/subject already pinned down or
    # being aggregated away), roll up avg/min/max/count within each group.
    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)

    students_by_year: dict[int, int] = defaultdict(int)
    for r in student_rows:
        students_by_year[r["year"]] += r["total_students"]

    results = []
    for yr in sorted(by_year):
        rollup = weighted_score_rollup(by_year[yr])
        if rollup is None:
            continue
        results.append({
            "region": region or "all",
            "year": yr,
            "subject": subject,
            "avg": rollup["avg"],
            "min": rollup["min"],
            "max": rollup["max"],
            "count": rollup["count"],
            "total_students": students_by_year.get(yr),
        })

    return {
        "filters": {"region": region or "all", "year": year, "subject": subject},
        "results": results,
    }


@app.get("/api/scores-by-region", response_model=ScoresByRegionResponse)
def get_scores_by_region(
    year: int | None = Query(None),
    subject: str | None = Query(None, description="Subject id; omitted = all subjects combined"),
):
    """Per-region score rollup, independent of alert data availability.

    Used by the map choropleth -- unlike /api/correlation, this has no
    dependency on the alerts file, so it still has values for years
    before the alert dataset starts (2022).
    """
    rows = _data["scores"]
    if year is not None:
        rows = [r for r in rows if r["year"] == year]
    if subject is not None:
        rows = [r for r in rows if r["subject"] == subject]

    by_region: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_region[r["region"]].append(r)

    results = []
    for rid in sorted(by_region):
        rollup = weighted_score_rollup(by_region[rid])
        if rollup is None:
            continue
        results.append({"region": rid, **rollup})

    return {
        "filters": {"year": year, "subject": subject},
        "results": results,
    }


@app.get("/api/scores-by-sex", response_model=ScoresBySexResponse)
def get_scores_by_sex(
    region: str | None = Query(None, description="Region id, or omitted/'all' for national aggregate"),
    subject: str | None = Query(None, description="Subject id; omitted = all subjects combined"),
):
    """Male vs. female average score per year, for the gender-split
    diverging chart. Rolled up across regions/subjects the same way
    /api/scores is when region/subject are omitted."""
    if region and region != "all" and region not in region_ids():
        raise HTTPException(404, f"Unknown region '{region}'")

    rows = _data["scores_by_sex"]
    if region and region != "all":
        rows = [r for r in rows if r["region"] == region]
    if subject is not None:
        rows = [r for r in rows if r["subject"] == subject]

    by_year_sex: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_year_sex[(r["year"], r["sex"])].append(r)

    years = sorted({y for y, _ in by_year_sex})
    results = []
    for yr in years:
        male_rollup = weighted_score_rollup(by_year_sex.get((yr, "male"), []))
        female_rollup = weighted_score_rollup(by_year_sex.get((yr, "female"), []))
        results.append({
            "year": yr,
            "male_avg": male_rollup["avg"] if male_rollup else None,
            "male_count": male_rollup["count"] if male_rollup else 0,
            "female_avg": female_rollup["avg"] if female_rollup else None,
            "female_count": female_rollup["count"] if female_rollup else 0,
        })

    return {
        "filters": {"region": region or "all", "subject": subject},
        "results": results,
    }


@app.get("/api/alerts", response_model=AlertsResponse)
def get_alerts(
    region: str | None = Query(None, description="Region id, or omitted/'all' for national aggregate"),
    year: int | None = Query(None),
):
    if region and region != "all" and region not in region_ids():
        raise HTTPException(404, f"Unknown region '{region}'")

    rows = _data["alerts"]
    if year is not None:
        rows = [r for r in rows if r["year"] == year]
    if region and region != "all":
        rows = [r for r in rows if r["region"] == region]

    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)

    results = []
    for yr in sorted(by_year):
        grp = by_year[yr]
        results.append({
            "region": region or "all",
            "year": yr,
            "alert_count": sum(r["alert_count"] for r in grp),
            "duration_all_min": round(sum(r["duration_all_min"] for r in grp), 1),
            "duration_excl_naive_min": round(sum(r["duration_excl_naive_min"] for r in grp), 1),
            "naive_count": sum(r["naive_count"] for r in grp),
        })

    return {
        "filters": {"region": region or "all", "year": year},
        "results": results,
        "note": _data["meta"]["notes"]["alert_duration"],
    }


@app.get("/api/alerts-daily", response_model=AlertsDailyResponse)
def get_alerts_daily(
    region: str | None = Query(None, description="Region id, or omitted/'all' for national total"),
):
    """Day-by-day alert count, not bucketed to a year -- feeds the
    granular alerts-over-time line chart."""
    if region and region != "all" and region not in region_ids():
        raise HTTPException(404, f"Unknown region '{region}'")

    rows = _data["alerts_daily"]
    if region and region != "all":
        rows = [r for r in rows if r["region"] == region]

    by_date: dict[str, dict] = defaultdict(lambda: {
        "alert_count": 0, "duration_all_min": 0.0, "duration_excl_naive_min": 0.0
    })
    for r in rows:
        agg = by_date[r["date"]]
        agg["alert_count"] += r["alert_count"]
        agg["duration_all_min"] += r["duration_all_min"]
        agg["duration_excl_naive_min"] += r["duration_excl_naive_min"]

    results = [
        {
            "date": d,
            "alert_count": v["alert_count"],
            "duration_all_min": round(v["duration_all_min"], 1),
            "duration_excl_naive_min": round(v["duration_excl_naive_min"], 1),
        }
        for d, v in sorted(by_date.items())
    ]

    return {
        "filters": {"region": region or "all"},
        "results": results,
    }


@app.get("/api/correlation", response_model=CorrelationResponse)
def get_correlation(
    year: int | None = Query(None, description="Omit to sum alerts/scores across all years"),
    subject: str | None = Query(None, description="Subject id; omitted = all subjects combined"),
):
    score_rows = _data["scores"]
    if year is not None:
        score_rows = [r for r in score_rows if r["year"] == year]
    if subject is not None:
        score_rows = [r for r in score_rows if r["subject"] == subject]

    alert_rows = _data["alerts"]
    if year is not None:
        alert_rows = [r for r in alert_rows if r["year"] == year]

    scores_by_region: dict[str, list[dict]] = defaultdict(list)
    for r in score_rows:
        scores_by_region[r["region"]].append(r)

    alerts_by_region: dict[str, list[dict]] = defaultdict(list)
    for r in alert_rows:
        alerts_by_region[r["region"]].append(r)

    region_label = {r["id"]: r["label"] for r in _data["meta"]["regions"]}

    points = []
    for rid in sorted(set(scores_by_region) & set(alerts_by_region)):
        score_rollup = weighted_score_rollup(scores_by_region[rid])
        if score_rollup is None:
            continue
        alert_grp = alerts_by_region[rid]
        points.append({
            "region": rid,
            "region_label": region_label.get(rid, rid),
            "alert_count": sum(a["alert_count"] for a in alert_grp),
            "avg_score": score_rollup["avg"],
            "duration_all_min": round(sum(a["duration_all_min"] for a in alert_grp), 1),
            "duration_excl_naive_min": round(sum(a["duration_excl_naive_min"] for a in alert_grp), 1),
        })

    r = pearson_correlation(
        [p["alert_count"] for p in points],
        [p["avg_score"] for p in points],
    )

    return {
        "filters": {"year": year, "subject": subject},
        "points": points,
        "pearson_r": round(r, 3) if r is not None else None,
        "disclaimer": _data["meta"]["notes"]["correlation_disclaimer"],
    }
