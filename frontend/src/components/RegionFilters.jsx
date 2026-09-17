const METRICS = [
  { id: 'avg', label: 'Avg' },
  { id: 'min', label: 'Min' },
  { id: 'max', label: 'Max' },
  { id: 'total_students', label: 'Students' },
]

export default function RegionFilters({
  regions,
  subjects,
  years,
  subject,
  year,
  metric,
  onSubjectChange,
  onYearChange,
  onMetricChange,
  selectedRegion,
  onReset,
}) {
  const selectedRegionMeta = regions.find((r) => r.id === selectedRegion)

  return (
    <div className="card">
      <p className="card-title">Filters</p>

      {selectedRegionMeta ? (
        <div className="selected-region-banner">
          <span>{selectedRegionMeta.label}</span>
          <button className="reset-btn" style={{ margin: 0 }} onClick={onReset}>
            Reset to all Ukraine
          </button>
        </div>
      ) : (
        <div className="selected-region-banner" style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-dim)' }}>
          <span>All Ukraine</span>
        </div>
      )}

      <div className="filters-row">
        <div className="field">
          <label htmlFor="subject-select">Subject</label>
          <select id="subject-select" value={subject} onChange={(e) => onSubjectChange(e.target.value)}>
            <option value="">All subjects (combined)</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="year-slider">Year — {year || 'All years'}</label>
          <input
            id="year-slider"
            type="range"
            className="year-slider"
            min={years[0]}
            max={years[years.length - 1]}
            step={1}
            value={year || years[years.length - 1]}
            onChange={(e) => onYearChange(e.target.value)}
          />
          <div className="toggle-group">
            <button
              className={`toggle-btn ${!year ? 'active' : ''}`}
              onClick={() => onYearChange('')}
            >
              All years
            </button>
          </div>
        </div>

        <div className="field">
          <label>Score chart metric</label>
          <div className="toggle-group">
            {METRICS.map((m) => (
              <button
                key={m.id}
                className={`toggle-btn ${metric === m.id ? 'active' : ''}`}
                onClick={() => onMetricChange(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
