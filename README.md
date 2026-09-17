# Ukraine Exam Scores & Wartime Disruption Dashboard

Explores NMT/ZNO exam results alongside Ukraine's air-raid alert history, by region and
year. **Exploratory/correlational only** — nothing here establishes that alerts caused any
change in scores.

## Data setup

Raw source files (not committed — too large for git) go in `backend/data/raw/`:

- One yearly exam CSV per year, 2016–2026 (ZNO 2016–2021, NMT 2022–2026). Filenames matching
  `backend/scripts/build_aggregates.py`'s `YEAR_CONFIG` (e.g. `OpenData2016.csv`,
  `Odata2023File.csv`, ...).
- `volunteer_data_en.csv` — air-raid alert history from
  [Vadimkin/ukrainian-air-raid-sirens-dataset](https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset).

## Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# One-time ETL: raw CSVs -> backend/data/processed/aggregates.json
python scripts/build_aggregates.py

# Serve the processed data
uvicorn app.main:app --port 8000 --reload
```

The API never reads `data/raw/` again after the ETL step — only the small processed JSON.
Re-run `build_aggregates.py` whenever the raw files change.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173` (or the next free port) and expects the API at
`http://localhost:8000`.

## Data notes (see `backend/app/aggregation.py` and `backend/scripts/build_aggregates.py` for
the authoritative details)

- Region names are matched between the two datasets via an explicit 25-entry mapping
  (Ukrainian oblast name ↔ transliterated alert-dataset name ↔ ISO 3166-2:UA code used for
  the map), confirmed during data exploration — not fuzzy-matched.
- Exam column schema differs by era (2016–2021 ZNO, 2022 wartime-reduced NMT, 2023–2026 NMT);
  the ETL script has one explicit column map per year rather than assuming a shared schema.
- 2022 offered only 3 subjects nationwide (Ukrainian Language, History of Ukraine,
  Mathematics) due to the wartime-simplified exam format.
- Score rows are counted only when their status indicates a real numeric result (credited, or
  sat-but-below-threshold); absent/annulled rows are excluded.
- Alert duration figures are split into "all" and "excluding naive" variants, since `naive=True`
  rows have a fabricated 30-minute placeholder end time rather than a measured one. Alert count
  is the recommended default metric since it isn't affected by that.
- The Ukraine oblast GeoJSON (`frontend/public/ukraine-oblasts.geojson`) is from
  [geoBoundaries](https://www.geoboundaries.org) (UKR ADM1, simplified), rewound with
  `@mapbox/geojson-rewind` for correct d3 ring winding.
