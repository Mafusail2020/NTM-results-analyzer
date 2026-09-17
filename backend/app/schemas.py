from pydantic import BaseModel


class RegionOut(BaseModel):
    id: str
    uk: str
    en: str
    label: str
    iso: str


class SubjectOut(BaseModel):
    id: str
    label: str


class RegionsResponse(BaseModel):
    regions: list[RegionOut]
    subjects: list[SubjectOut]
    years: list[int]
    notes: dict[str, str]


class ScoreOut(BaseModel):
    region: str
    year: int
    subject: str | None = None
    avg: float | None = None
    min: float | None = None
    max: float | None = None
    count: int
    total_students: int | None = None


class ScoresResponse(BaseModel):
    filters: dict
    results: list[ScoreOut]


class RegionScoreOut(BaseModel):
    region: str
    avg: float
    min: float
    max: float
    count: int


class ScoresByRegionResponse(BaseModel):
    filters: dict
    results: list[RegionScoreOut]


class AlertOut(BaseModel):
    region: str
    year: int
    alert_count: int
    duration_all_min: float
    duration_excl_naive_min: float
    naive_count: int


class AlertsResponse(BaseModel):
    filters: dict
    results: list[AlertOut]
    note: str


class ScoreBySexOut(BaseModel):
    year: int
    male_avg: float | None = None
    male_count: int = 0
    female_avg: float | None = None
    female_count: int = 0


class ScoresBySexResponse(BaseModel):
    filters: dict
    results: list[ScoreBySexOut]


class AlertDailyOut(BaseModel):
    date: str
    alert_count: int
    duration_all_min: float
    duration_excl_naive_min: float


class AlertsDailyResponse(BaseModel):
    filters: dict
    results: list[AlertDailyOut]


class CorrelationPoint(BaseModel):
    region: str
    region_label: str
    alert_count: int
    avg_score: float
    duration_all_min: float
    duration_excl_naive_min: float


class CorrelationResponse(BaseModel):
    filters: dict
    points: list[CorrelationPoint]
    pearson_r: float | None
    disclaimer: str
