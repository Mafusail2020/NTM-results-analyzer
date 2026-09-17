"""One-time ETL: raw NMT/ZNO yearly CSVs + air-raid alert CSV -> a single
small JSON file the FastAPI app serves at request time.

Run once (from backend/):
    python scripts/build_aggregates.py

Raw inputs are read from backend/data/raw/ and are never touched again
after this script produces backend/data/processed/aggregates.json.

Schema notes (see project README for the full data-exploration writeup):
- 2016-2021 ("ZNO"): one Test/TestStatus/Ball100 column group per subject,
  subject encoded in the column name. Column casing differs by year.
- 2022 ("NMT", wartime-reduced): only 3 subjects were offered nationwide
  (Ukrainian Language, History of Ukraine, Mathematics), encoded as
  generic Block1/Block2/Block3 columns in that fixed order, with a single
  TestStatus shared across all three blocks for a row.
- 2023-2026 ("NMT"): subject-named BlockBall100/BlockStatus columns;
  the subject list itself grows over time (Geography and Ukrainian
  Literature blocks appear from 2024 on).
- Ball100 columns use a comma decimal separator and encode missing values
  as either an empty string or the literal string "null".
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.aggregation import ALERT_REGION_TO_ID, EXAM_REGION_TO_ID, REGIONS  # noqa: E402

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUT_PATH = OUT_DIR / "aggregates.json"

# A row counts toward score stats if its status is "credited" (real scaled
# score, used as-is) or explicitly "below threshold" (sat the exam, failed
# to clear the pass threshold -- the source data gives these Ball100 ==
# 0.0 exactly, a sentinel for "no scaled score computed", not a real
# point value). Below-threshold rows are floored to FLOOR_SCORE instead of
# being dropped, so a high-fail year still pulls the average down instead
# of vanishing entirely. FLOOR_SCORE is the scale's real minimum *passing*
# score, so this is a conservative proxy -- true below-threshold
# performance is unknown and presumably lower.
# "Не з'явився" (absent) and "Анульовано" (annulled) are excluded outright:
# no exam was meaningfully sat, so there's no reasonable score to assign.
VALID_STATUSES = {"Зараховано"}
VALID_STATUSES_2016 = {"Отримав результат"}
BELOW_THRESHOLD_STATUSES = {"Не подолав поріг"}
BELOW_THRESHOLD_STATUSES_2016 = {"Не склав"}
FLOOR_SCORE = 100.0

SUBJECT_LABELS = {
    "ukr": "Ukrainian Language",
    "uml": "Ukrainian Language & Literature",
    "ukrlit": "Ukrainian Literature",
    "hist": "History of Ukraine",
    "math": "Mathematics",
    "phys": "Physics",
    "chem": "Chemistry",
    "bio": "Biology",
    "geo": "Geography",
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish",
    "rus": "Russian",
}


def cols(pairs: dict[str, tuple[str, str]]) -> dict[str, dict[str, str]]:
    """pairs: subject -> (ball_col, status_col)"""
    return {k: {"ball": v[0], "status": v[1]} for k, v in pairs.items()}


# Per-year source config, built from the exact headers captured during
# data exploration (see project notes / conversation history).
YEAR_CONFIG = {
    2016: dict(
        file="OpenData2016.csv", encoding="cp1251", region_col="Regname", outid_col="OutID",
        era="named", subjects=cols({
            "ukr": ("UkrBall100", "UkrTestStatus"),
            "hist": ("HistBall100", "HistTestStatus"),
            "math": ("MathBall100", "MathTestStatus"),
            "phys": ("PhysBall100", "PhysTestStatus"),
            "chem": ("ChemBall100", "ChemTestStatus"),
            "bio": ("BioBall100", "BioTestStatus"),
            "geo": ("GeoBall100", "GeoTestStatus"),
            "eng": ("EngBall100", "EngTestStatus"),
            "fra": ("FrBall100", "FrTestStatus"),
            "deu": ("DeuBall100", "DeuTestStatus"),
            "spa": ("SpBall100", "SpTestStatus"),
            "rus": ("RusBall100", "RusTestStatus"),
        }),
    ),
    2017: dict(
        file="OpenData2017.csv", encoding="utf-8-sig", region_col="REGNAME", outid_col="OUTID",
        era="named", subjects=cols({
            "ukr": ("UKRBALL100", "UKRTESTSTATUS"),
            "hist": ("HISTBALL100", "HISTTESTSTATUS"),
            "math": ("MATHBALL100", "MATHTESTSTATUS"),
            "phys": ("PHYSBALL100", "PHYSTESTSTATUS"),
            "chem": ("CHEMBALL100", "CHEMTESTSTATUS"),
            "bio": ("BIOBALL100", "BIOTESTSTATUS"),
            "geo": ("GEOBALL100", "GEOTESTSTATUS"),
            "eng": ("ENGBALL100", "ENGTESTSTATUS"),
            "fra": ("FRABALL100", "FRATESTSTATUS"),
            "deu": ("DEUBALL100", "DEUTESTSTATUS"),
            "spa": ("SPABALL100", "SPATESTSTATUS"),
            "rus": ("RUSBALL100", "RUSTESTSTATUS"),
        }),
    ),
    2018: dict(
        file="OpenData2018.csv", encoding="utf-8-sig", region_col="REGNAME", outid_col="OUTID",
        era="named", subjects=cols({
            "ukr": ("UkrBall100", "UkrTestStatus"),
            "hist": ("histBall100", "histTestStatus"),
            "math": ("mathBall100", "mathTestStatus"),
            "phys": ("physBall100", "physTestStatus"),
            "chem": ("chemBall100", "chemTestStatus"),
            "bio": ("bioBall100", "bioTestStatus"),
            "geo": ("geoBall100", "geoTestStatus"),
            "eng": ("engBall100", "engTestStatus"),
            "fra": ("fraBall100", "fraTestStatus"),
            "deu": ("deuBall100", "deuTestStatus"),
            "spa": ("spaBall100", "spaTestStatus"),
        }),
    ),
    2019: dict(
        file="Odata2019File.csv", encoding="cp1251", region_col="REGNAME", outid_col="OUTID",
        era="named", subjects=cols({
            "ukr": ("UkrBall100", "UkrTestStatus"),
            "hist": ("histBall100", "histTestStatus"),
            "math": ("mathBall100", "mathTestStatus"),
            "phys": ("physBall100", "physTestStatus"),
            "chem": ("chemBall100", "chemTestStatus"),
            "bio": ("bioBall100", "bioTestStatus"),
            "geo": ("geoBall100", "geoTestStatus"),
            "eng": ("engBall100", "engTestStatus"),
            "fra": ("fraBall100", "fraTestStatus"),
            "deu": ("deuBall100", "deuTestStatus"),
            "spa": ("spaBall100", "spaTestStatus"),
        }),
    ),
    2020: dict(
        file="Odata2020File.csv", encoding="cp1251", region_col="REGNAME", outid_col="OUTID",
        era="named", subjects=cols({
            "ukr": ("UkrBall100", "UkrTestStatus"),
            "hist": ("histBall100", "histTestStatus"),
            "math": ("mathBall100", "mathTestStatus"),
            "phys": ("physBall100", "physTestStatus"),
            "chem": ("chemBall100", "chemTestStatus"),
            "bio": ("bioBall100", "bioTestStatus"),
            "geo": ("geoBall100", "geoTestStatus"),
            "eng": ("engBall100", "engTestStatus"),
            "fra": ("fraBall100", "fraTestStatus"),
            "deu": ("deuBall100", "deuTestStatus"),
            "spa": ("spaBall100", "spaTestStatus"),
        }),
    ),
    2021: dict(
        file="Odata2021File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="OUTID",
        era="named", subjects=cols({
            "uml": ("UMLBall100", "UMLTestStatus"),
            "ukr": ("UkrBall100", "UkrTestStatus"),
            "hist": ("HistBall100", "HistTestStatus"),
            "math": ("MathBall100", "MathTestStatus"),
            "phys": ("PhysBall100", "PhysTestStatus"),
            "chem": ("ChemBall100", "ChemTestStatus"),
            "bio": ("BioBall100", "BioTestStatus"),
            "geo": ("GeoBall100", "GeoTestStatus"),
            "eng": ("EngBall100", "EngTestStatus"),
            "fra": ("FraBall100", "FraTestStatus"),
            "deu": ("DeuBall100", "DeuTestStatus"),
            "spa": ("SpaBall100", "SpaTestStatus"),
        }),
    ),
    2022: dict(
        file="Odata2022File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="OUTID",
        era="block2022", status_col="TestStatus", subjects={
            "ukr": {"ball": "Block1Ball100"},
            "hist": {"ball": "Block2Ball100"},
            "math": {"ball": "Block3Ball100"},
        },
    ),
    2023: dict(
        file="Odata2023File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="outid",
        era="named", subjects=cols({
            "ukr": ("UkrBlockBall100", "UkrBlockStatus"),
            "hist": ("HistBlockBall100", "HistBlockStatus"),
            "math": ("MathBlockBall100", "MathBlockStatus"),
            "phys": ("PhysBlockBall100", "PhysBlockStatus"),
            "chem": ("ChemBlockBall100", "ChemBlockStatus"),
            "bio": ("BioBlockBall100", "BioBlockStatus"),
            "eng": ("EngBlockBall100", "EngBlockStatus"),
            "fra": ("FraBlockBall100", "FraBlockStatus"),
            "deu": ("DeuBlockBall100", "DeuBlockStatus"),
            "spa": ("SpaBlockBall100", "SpaBlockStatus"),
        }),
    ),
    2024: dict(
        file="Odata2024File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="outid",
        era="named", subjects=cols({
            "ukr": ("UkrBlockBall100", "UkrBlockStatus"),
            "hist": ("HistBlockBall100", "HistBlockStatus"),
            "math": ("MathBlockBall100", "MathBlockStatus"),
            "phys": ("PhysBlockBall100", "PhysBlockStatus"),
            "chem": ("ChemBlockBall100", "ChemBlockStatus"),
            "bio": ("BioBlockBall100", "BioBlockStatus"),
            "geo": ("GeoBlockBall100", "GeoBlockStatus"),
            "eng": ("EngBlockBall100", "EngBlockStatus"),
            "fra": ("FraBlockBall100", "FraBlockStatus"),
            "deu": ("DeuBlockBall100", "DeuBlockStatus"),
            "spa": ("SpaBlockBall100", "SpaBlockStatus"),
            "ukrlit": ("UkrLitBlockBall100", "UkrLitBlockStatus"),
        }),
    ),
    2025: dict(
        file="Odata2025File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="outid",
        era="named", subjects=cols({
            "ukr": ("UkrBlockBall100", "UkrBlockStatus"),
            "hist": ("HistBlockBall100", "HistBlockStatus"),
            "math": ("MathBlockBall100", "MathBlockStatus"),
            "phys": ("PhysBlockBall100", "PhysBlockStatus"),
            "chem": ("ChemBlockBall100", "ChemBlockStatus"),
            "bio": ("BioBlockBall100", "BioBlockStatus"),
            "geo": ("GeoBlockBall100", "GeoBlockStatus"),
            "eng": ("EngBlockBall100", "EngBlockStatus"),
            "fra": ("FraBlockBall100", "FraBlockStatus"),
            "deu": ("DeuBlockBall100", "DeuBlockStatus"),
            "spa": ("SpaBlockBall100", "SpaBlockStatus"),
            "ukrlit": ("UkrLitBlockBall100", "UkrLitBlockStatus"),
        }),
    ),
    2026: dict(
        file="Odata2026File.csv", encoding="utf-8-sig", region_col="RegName", outid_col="outid",
        era="named", subjects=cols({
            "ukr": ("UkrBlockBall100", "UkrBlockStatus"),
            "hist": ("HistBlockBall100", "HistBlockStatus"),
            "math": ("MathBlockBall100", "MathBlockStatus"),
            "phys": ("PhysBlockBall100", "PhysBlockStatus"),
            "chem": ("ChemBlockBall100", "ChemBlockStatus"),
            "bio": ("BioBlockBall100", "BioBlockStatus"),
            "geo": ("GeoBlockBall100", "GeoBlockStatus"),
            "eng": ("EngBlockBall100", "EngBlockStatus"),
            "fra": ("FraBlockBall100", "FraBlockStatus"),
            "deu": ("DeuBlockBall100", "DeuBlockStatus"),
            "spa": ("SpaBlockBall100", "SpaBlockStatus"),
            "ukrlit": ("UkrLitBlockBall100", "UkrLitBlockStatus"),
        }),
    ),
}

CHUNK_SIZE = 200_000

# SexTypeName column casing matches the header exactly captured per year
# (see project notes); vocabulary is identical across all 11 files.
SEX_COL_BY_YEAR = {
    2016: "SexTypeName", 2017: "SEXTYPENAME", 2018: "SEXTYPENAME",
    2019: "SEXTYPENAME", 2020: "SEXTYPENAME", 2021: "SexTypeName",
    2022: "SexTypeName", 2023: "SexTypeName", 2024: "SexTypeName",
    2025: "SexTypeName", 2026: "SexTypeName",
}
SEX_MAP = {"чоловіча": "male", "жіноча": "female"}


def process_year(year: int, cfg: dict, score_agg: dict, student_sets: dict, sex_agg: dict) -> None:
    path = RAW_DIR / cfg["file"]
    region_col = cfg["region_col"]
    outid_col = cfg["outid_col"]
    sex_col = SEX_COL_BY_YEAR[year]
    subjects = cfg["subjects"]
    valid_statuses = VALID_STATUSES_2016 if year == 2016 else VALID_STATUSES
    below_statuses = BELOW_THRESHOLD_STATUSES_2016 if year == 2016 else BELOW_THRESHOLD_STATUSES

    usecols = [region_col, outid_col, sex_col]
    for s in subjects.values():
        usecols.append(s["ball"])
        if "status" in s:
            usecols.append(s["status"])
    if cfg["era"] == "block2022":
        usecols.append(cfg["status_col"])
    usecols = list(dict.fromkeys(usecols))  # de-dupe, keep order

    reader = pd.read_csv(
        path,
        sep=";",
        usecols=usecols,
        encoding=cfg["encoding"],
        decimal=",",
        na_values=["null", "NULL", ""],
        dtype={outid_col: str},
        chunksize=CHUNK_SIZE,
        low_memory=False,
    )

    row_count = 0
    for chunk in reader:
        row_count += len(chunk)
        region_id = chunk[region_col].map(EXAM_REGION_TO_ID)
        valid_region = region_id.notna()
        sex_id = chunk[sex_col].map(SEX_MAP)

        shared_status_ok = None
        if cfg["era"] == "block2022":
            shared_status_ok = chunk[cfg["status_col"]].isin(valid_statuses)

        for subj, colinfo in subjects.items():
            ball = pd.to_numeric(chunk[colinfo["ball"]], errors="coerce")
            if "status" in colinfo:
                status_col = chunk[colinfo["status"]]
                credited = status_col.isin(valid_statuses)
                below = status_col.isin(below_statuses)
            else:
                # 2022's shared status has no separate below-threshold value;
                # a credited row with Ball100 == 0 on this specific block is
                # that era's equivalent (see FLOOR_SCORE comment above).
                credited = shared_status_ok
                below = pd.Series(False, index=chunk.index)

            has_real_score = ball.notna() & (ball > 0)
            mask_passed = valid_region & credited & has_real_score
            mask_failed = valid_region & (below | (credited & (ball == 0)))
            mask = mask_passed | mask_failed
            if not mask.any():
                continue

            effective_ball = pd.Series(FLOOR_SCORE, index=chunk.index)
            effective_ball[mask_passed] = ball[mask_passed]

            sub_region = region_id[mask]
            sub_ball = effective_ball[mask]
            for rid, grp in sub_ball.groupby(sub_region):
                key = (rid, year, subj)
                agg = score_agg[key]
                agg["sum"] += float(grp.sum())
                agg["count"] += int(grp.count())
                agg["min"] = grp.min() if agg["min"] is None else min(agg["min"], grp.min())
                agg["max"] = grp.max() if agg["max"] is None else max(agg["max"], grp.max())

            sub_sex = sex_id[mask]
            for (rid, sex), grp in sub_ball.groupby([sub_region, sub_sex]):
                if pd.isna(sex):
                    continue
                key = (rid, year, subj, sex)
                agg = sex_agg[key]
                agg["sum"] += float(grp.sum())
                agg["count"] += int(grp.count())
                agg["min"] = grp.min() if agg["min"] is None else min(agg["min"], grp.min())
                agg["max"] = grp.max() if agg["max"] is None else max(agg["max"], grp.max())

        # Distinct student count per (region, year), across any subject sat.
        any_subject_mask = valid_region.copy()
        sub_region_all = region_id[any_subject_mask]
        sub_outid_all = chunk.loc[any_subject_mask, outid_col]
        for rid, ids in sub_outid_all.groupby(sub_region_all):
            student_sets[(rid, year)].update(ids.dropna().tolist())

    print(f"  {year}: {row_count:,} rows read from {cfg['file']}")


def build_scores() -> tuple[list[dict], list[dict], list[dict]]:
    score_agg: dict[tuple[str, int, str], dict] = defaultdict(
        lambda: {"sum": 0.0, "count": 0, "min": None, "max": None}
    )
    sex_agg: dict[tuple[str, int, str, str], dict] = defaultdict(
        lambda: {"sum": 0.0, "count": 0, "min": None, "max": None}
    )
    student_sets: dict[tuple[str, int], set] = defaultdict(set)

    print("Processing exam files...")
    for year, cfg in sorted(YEAR_CONFIG.items()):
        process_year(year, cfg, score_agg, student_sets, sex_agg)

    scores = []
    for (region_id, year, subject), agg in score_agg.items():
        if agg["count"] == 0:
            continue
        scores.append({
            "region": region_id,
            "year": year,
            "subject": subject,
            "avg": round(agg["sum"] / agg["count"], 2),
            "min": agg["min"],
            "max": agg["max"],
            "count": agg["count"],
        })

    scores_by_sex = []
    for (region_id, year, subject, sex), agg in sex_agg.items():
        if agg["count"] == 0:
            continue
        scores_by_sex.append({
            "region": region_id,
            "year": year,
            "subject": subject,
            "sex": sex,
            "avg": round(agg["sum"] / agg["count"], 2),
            "min": agg["min"],
            "max": agg["max"],
            "count": agg["count"],
        })

    student_counts = [
        {"region": region_id, "year": year, "total_students": len(ids)}
        for (region_id, year), ids in student_sets.items()
    ]
    return scores, student_counts, scores_by_sex


def build_alerts() -> tuple[list[dict], list[dict]]:
    print("Processing air-raid alert file...")
    path = RAW_DIR / "volunteer_data_en.csv"
    df = pd.read_csv(path)
    df["started_at"] = pd.to_datetime(df["started_at"], utc=True)
    df["finished_at"] = pd.to_datetime(df["finished_at"], utc=True)
    df["duration_min"] = (df["finished_at"] - df["started_at"]).dt.total_seconds() / 60.0
    df["year"] = df["started_at"].dt.year
    df["region_id"] = df["region"].map(ALERT_REGION_TO_ID)

    unmapped = df.loc[df["region_id"].isna(), "region"].unique()
    if len(unmapped):
        print(f"  WARNING: unmapped alert regions dropped: {list(unmapped)}")
    df = df.dropna(subset=["region_id"])

    # A handful of rows (verified against the raw file, none flagged
    # `naive`) have a finished_at that is clearly mismatched with the
    # wrong started_at -- durations up to ~178 hours for what the source
    # otherwise treats as a single siren activation. No real air-raid
    # alert plausibly runs that long, so these are a second, distinct
    # data-quality failure mode from `naive` (which is a source-declared
    # fabricated placeholder) -- this one is a corrupted real timestamp
    # pair. They still represent a real alert (kept in alert_count), but
    # their duration is excluded from every duration sum, the same way
    # naive rows can be excluded via duration_excl_naive_min.
    IMPLAUSIBLE_DURATION_MIN = 24 * 60
    implausible = df["duration_min"] > IMPLAUSIBLE_DURATION_MIN
    if implausible.any():
        print(f"  WARNING: {implausible.sum()} alert rows have an implausible "
              f"duration (>{IMPLAUSIBLE_DURATION_MIN/60:.0f}h); excluded from "
              f"duration sums, kept in alert_count")
    df["duration_min_plausible"] = df["duration_min"].where(~implausible, 0.0)

    alerts = []
    for (region_id, year), grp in df.groupby(["region_id", "year"]):
        non_naive = grp[~grp["naive"]]
        alerts.append({
            "region": region_id,
            "year": int(year),
            "alert_count": int(len(grp)),
            "duration_all_min": round(float(grp["duration_min_plausible"].sum()), 1),
            "duration_excl_naive_min": round(float(non_naive["duration_min_plausible"].sum()), 1),
            "naive_count": int(grp["naive"].sum()),
        })

    # Daily rollup, for the granular alerts-over-time line chart -- not
    # rounded to a year bucket like `alerts` above. Duration is attributed
    # to the day the alert *started* (same convention as `date` itself),
    # so an alert spanning midnight counts entirely on its start day.
    df["date"] = df["started_at"].dt.date
    alerts_daily = []
    for (region_id, date), grp in df.groupby(["region_id", "date"]):
        non_naive = grp[~grp["naive"]]
        alerts_daily.append({
            "region": region_id,
            "date": date.isoformat(),
            "alert_count": int(len(grp)),
            "duration_all_min": round(float(grp["duration_min_plausible"].sum()), 1),
            "duration_excl_naive_min": round(float(non_naive["duration_min_plausible"].sum()), 1),
        })
    alerts_daily.sort(key=lambda r: (r["region"], r["date"]))

    return alerts, alerts_daily


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    scores, student_counts, scores_by_sex = build_scores()
    alerts, alerts_daily = build_alerts()

    years = sorted({s["year"] for s in scores})
    subjects_present = sorted({s["subject"] for s in scores})

    output = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "years": years,
            "subjects": [
                {"id": s, "label": SUBJECT_LABELS.get(s, s)} for s in subjects_present
            ],
            "regions": [
                {"id": rid, "uk": info["uk"], "en": info["en"], "label": info["label"], "iso": info["iso"]}
                for rid, info in REGIONS.items()
            ],
            "notes": {
                "2022": (
                    "2022 NMT offered only 3 subjects nationwide (Ukrainian, "
                    "History, Math) — other subjects have no 2022 data point."
                ),
                "alert_duration": (
                    "Includes estimated durations for alerts with no recorded "
                    "end time; excludes a few rows with corrupted end times. "
                    "Alert count is the more reliable metric."
                ),
                "score_filter": (
                    "Score aggregates include credited rows at their real "
                    "scaled score, plus sat-but-below-threshold rows floored "
                    "to 100 (the scale's minimum passing score) as a "
                    "conservative stand-in for their true, unrecorded score. "
                    "This means a year/region with a higher failure rate "
                    "will show a lower average, by design. Absent and "
                    "annulled rows are excluded outright."
                ),
                "correlation_disclaimer": (
                    "Correlational only — does not establish that alerts "
                    "caused a change in scores."
                ),
            },
        },
        "scores": scores,
        "scores_by_sex": scores_by_sex,
        "student_counts": student_counts,
        "alerts": alerts,
        "alerts_daily": alerts_daily,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    print(f"\nWrote {OUT_PATH}")
    print(f"  scores rows: {len(scores):,}")
    print(f"  scores_by_sex rows: {len(scores_by_sex):,}")
    print(f"  student_count rows: {len(student_counts):,}")
    print(f"  alert rows: {len(alerts):,}")
    print(f"  alert daily rows: {len(alerts_daily):,}")


if __name__ == "__main__":
    main()
