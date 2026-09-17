const BASE_URL = 'http://localhost:8000/api'

async function get(path, params = {}) {
  const url = new URL(`${BASE_URL}${path}`)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v)
  })
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`)
  }
  return res.json()
}

export const fetchRegions = () => get('/regions')

export const fetchScores = ({ region, year, subject } = {}) =>
  get('/scores', { region, year, subject })

export const fetchScoresByRegion = ({ year, subject } = {}) =>
  get('/scores-by-region', { year, subject })

export const fetchScoresBySex = ({ region, subject } = {}) =>
  get('/scores-by-sex', { region, subject })

export const fetchAlerts = ({ region, year } = {}) =>
  get('/alerts', { region, year })

export const fetchAlertsDaily = ({ region } = {}) =>
  get('/alerts-daily', { region })

export const fetchCorrelation = ({ year, subject } = {}) =>
  get('/correlation', { year, subject })
