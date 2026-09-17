import { useEffect, useMemo, useState } from 'react'
import UkraineMap from './components/UkraineMap.jsx'
import RegionFilters from './components/RegionFilters.jsx'
import ScoreChart from './components/ScoreChart.jsx'
import GenderPyramidChart from './components/GenderPyramidChart.jsx'
import AlertsLineChart from './components/AlertsLineChart.jsx'
import CorrelationScatter from './components/CorrelationScatter.jsx'
import {
  fetchRegions,
  fetchScores,
  fetchScoresByRegion,
  fetchScoresBySex,
  fetchCorrelation,
  fetchAlerts,
  fetchAlertsDaily,
} from './api.js'

function toDecimalYear(dateStr) {
  const d = new Date(`${dateStr}T00:00:00Z`)
  const year = d.getUTCFullYear()
  const startOfYear = Date.UTC(year, 0, 1)
  const startOfNextYear = Date.UTC(year + 1, 0, 1)
  return year + (d.getTime() - startOfYear) / (startOfNextYear - startOfYear)
}

// Background photo fades from some color (2016, peacetime) to fully grey
// by 2022 (the invasion) and stays grey for every later year and for
// "all years" -- a visual echo of the score chart's own 2022 turn.
const BG_PEACE_YEAR = 2016
const BG_WAR_YEAR = 2022
const BG_GRAYSCALE_PEACE = 0.35
const BG_GRAYSCALE_WAR = 0.92

function grayscaleForYear(year) {
  if (!year) return BG_GRAYSCALE_WAR
  const y = Number(year)
  if (y <= BG_PEACE_YEAR) return BG_GRAYSCALE_PEACE
  if (y >= BG_WAR_YEAR) return BG_GRAYSCALE_WAR
  const t = (y - BG_PEACE_YEAR) / (BG_WAR_YEAR - BG_PEACE_YEAR)
  return BG_GRAYSCALE_PEACE + t * (BG_GRAYSCALE_WAR - BG_GRAYSCALE_PEACE)
}

function buildDailyGrid(years, dailyRows) {
  if (!years.length) return []
  const byDate = {}
  dailyRows.forEach((r) => { byDate[r.date] = r })
  const start = new Date(Date.UTC(years[0], 0, 1))
  const end = new Date(Date.UTC(years[years.length - 1], 11, 31))
  const out = []
  for (let d = start; d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
    const dateStr = d.toISOString().slice(0, 10)
    const row = byDate[dateStr]
    out.push({
      x: toDecimalYear(dateStr),
      date: dateStr,
      alert_count: row?.alert_count ?? 0,
      hours_active: row ? row.duration_all_min / 60 : 0,
    })
  }
  return out
}

export default function App() {
  const [meta, setMeta] = useState(null)
  const [metaError, setMetaError] = useState(null)

  const [selectedRegion, setSelectedRegion] = useState(null)
  const [subject, setSubject] = useState('')
  const [year, setYear] = useState('')
  const [metric, setMetric] = useState('avg')

  const [scoreData, setScoreData] = useState([])
  const [scoresByRegion, setScoresByRegion] = useState([])
  const [scoresBySex, setScoresBySex] = useState([])
  const [correlation, setCorrelation] = useState(null)
  const [alertSummary, setAlertSummary] = useState(null)
  const [alertsDaily, setAlertsDaily] = useState([])

  useEffect(() => {
    fetchRegions().then(setMeta).catch((e) => setMetaError(e.message))
  }, [])

  useEffect(() => {
    document.documentElement.style.setProperty('--bg-grayscale', grayscaleForYear(year))
  }, [year])

  useEffect(() => {
    fetchScores({ region: selectedRegion, subject })
      .then((res) => setScoreData(res.results))
      .catch(() => setScoreData([]))
  }, [selectedRegion, subject])

  useEffect(() => {
    fetchScoresByRegion({ year, subject })
      .then((res) => setScoresByRegion(res.results))
      .catch(() => setScoresByRegion([]))
  }, [year, subject])

  useEffect(() => {
    fetchScoresBySex({ region: selectedRegion, subject })
      .then((res) => setScoresBySex(res.results))
      .catch(() => setScoresBySex([]))
  }, [selectedRegion, subject])

  useEffect(() => {
    fetchCorrelation({ year, subject })
      .then(setCorrelation)
      .catch(() => setCorrelation(null))
  }, [year, subject])

  useEffect(() => {
    fetchAlerts({ region: selectedRegion, year })
      .then((res) => setAlertSummary(res.results.at(-1) ?? null))
      .catch(() => setAlertSummary(null))
  }, [selectedRegion, year])

  useEffect(() => {
    fetchAlertsDaily({ region: selectedRegion })
      .then((res) => setAlertsDaily(res.results))
      .catch(() => setAlertsDaily([]))
  }, [selectedRegion])

  const regionLabel = useMemo(() => {
    if (!selectedRegion || !meta) return 'All Ukraine'
    return meta.regions.find((r) => r.id === selectedRegion)?.label ?? selectedRegion
  }, [selectedRegion, meta])

  const subjectLabel = useMemo(() => {
    if (!subject || !meta) return 'All subjects (combined)'
    return meta.subjects.find((s) => s.id === subject)?.label ?? subject
  }, [subject, meta])

  const mapMetricByRegion = useMemo(() => {
    const out = {}
    scoresByRegion.forEach((r) => { out[r.region] = r.avg })
    return out
  }, [scoresByRegion])

  const alertsDailySeries = useMemo(() => {
    if (!meta) return []
    return buildDailyGrid(meta.years, alertsDaily)
  }, [meta, alertsDaily])

  if (metaError) {
    return (
      <div className="app-shell">
        <p className="empty-note">
          Could not reach the API at localhost:8000 ({metaError}). Is the backend running?
        </p>
      </div>
    )
  }

  if (!meta) {
    return <div className="app-shell"><p className="loading">Loading…</p></div>
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Ukraine Exam Scores & Wartime Disruption</h1>
      </header>

      <div className="layout-grid">
        <div>
          <RegionFilters
            regions={meta.regions}
            subjects={meta.subjects}
            years={meta.years}
            subject={subject}
            year={year}
            metric={metric}
            onSubjectChange={setSubject}
            onYearChange={setYear}
            onMetricChange={setMetric}
            selectedRegion={selectedRegion}
            onReset={() => setSelectedRegion(null)}
          />

          <div className="card">
            <p className="card-title">Oblast map</p>
            <UkraineMap
              regions={meta.regions}
              metricByRegion={mapMetricByRegion}
              metricLabel="Avg score"
              selectedRegion={selectedRegion}
              onSelect={(id) => setSelectedRegion((cur) => (cur === id ? null : id))}
            />
          </div>

          {alertSummary && (
            <div className="card">
              <p className="card-title">Air-raid alerts — {regionLabel}{year ? `, ${year}` : ' (all years)'}</p>
              <div className="stat-row">
                <div className="stat">
                  <span className="value">{alertSummary.alert_count}</span>
                  <span className="label">Alert count</span>
                </div>
                <div className="stat">
                  <span className="value">{Math.round(alertSummary.duration_all_min / 60)}h</span>
                  <span className="label">Total duration</span>
                </div>
              </div>
              <p className="chart-caption">{meta.notes.alert_duration}</p>
            </div>
          )}
        </div>

        <div>
          <div className="card">
            <p className="card-title">Score trend — {regionLabel}</p>
            <ScoreChart
              data={scoreData}
              metric={metric}
              regionLabel={regionLabel}
              subjectLabel={subjectLabel}
              years={meta.years}
            />
            {meta.notes['2022'] && (
              <p className="chart-caption">{meta.notes['2022']}</p>
            )}
          </div>

          <div className="card">
            <p className="card-title">Score by gender — {regionLabel}</p>
            <GenderPyramidChart
              data={scoresBySex}
              regionLabel={regionLabel}
              subjectLabel={subjectLabel}
            />
          </div>

          <div className="card">
            <p className="card-title">Alerts over time — {regionLabel}</p>
            <AlertsLineChart
              data={alertsDailySeries}
              years={meta.years}
              regionLabel={regionLabel}
              durationNote={meta.notes.alert_duration}
            />
          </div>

          <div className="card">
            <p className="card-title">
              Alert exposure vs. avg score {year ? `— ${year}` : '— all years summed'} — {subjectLabel}
            </p>
            {correlation && (
              <CorrelationScatter
                points={correlation.points}
                pearsonR={correlation.pearson_r}
                disclaimer={correlation.disclaimer}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
