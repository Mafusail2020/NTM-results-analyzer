import { useMemo } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ZAxis,
} from 'recharts'

function linearRegression(points) {
  const n = points.length
  if (n < 2) return null
  const sumX = points.reduce((a, p) => a + p.alert_count, 0)
  const sumY = points.reduce((a, p) => a + p.avg_score, 0)
  const sumXY = points.reduce((a, p) => a + p.alert_count * p.avg_score, 0)
  const sumXX = points.reduce((a, p) => a + p.alert_count * p.alert_count, 0)
  const denom = n * sumXX - sumX * sumX
  if (denom === 0) return null
  const slope = (n * sumXY - sumX * sumY) / denom
  const intercept = (sumY - slope * sumX) / n
  return { slope, intercept }
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="tooltip-box">
      <div><strong>{p.region_label}</strong></div>
      <div>Alerts: {p.alert_count}</div>
      <div>Avg score: {p.avg_score}</div>
    </div>
  )
}

export default function CorrelationScatter({ points, pearsonR, disclaimer }) {
  const trendSegment = useMemo(() => {
    const reg = linearRegression(points)
    if (!reg || !points.length) return null
    const xs = points.map((p) => p.alert_count)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    return [
      { x: minX, y: reg.slope * minX + reg.intercept },
      { x: maxX, y: reg.slope * maxX + reg.intercept },
    ]
  }, [points])

  if (!points.length) {
    return <p className="empty-note">No overlapping alert/score data for this selection.</p>
  }

  return (
    <div>
      <div className="stat-row">
        <div className="stat">
          <span className="value">{pearsonR ?? '—'}</span>
          <span className="label">Pearson r</span>
        </div>
        <div className="stat">
          <span className="value">{points.length}</span>
          <span className="label">Regions plotted</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#2a2a32" />
          <XAxis
            type="number"
            dataKey="alert_count"
            name="Alert count"
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
            label={{ value: 'Alert count', position: 'insideBottom', offset: -4, fill: '#9a9aa8', fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="avg_score"
            name="Avg score"
            domain={[100, 200]}
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
            label={{ value: 'Avg score', angle: -90, position: 'insideLeft', fill: '#9a9aa8', fontSize: 12 }}
          />
          <ZAxis range={[70, 70]} />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#34343e' }} />
          {/* Trend line is a decorative ReferenceLine, not a data series --
              keeping it out of the tooltip/axis-tracking system is what
              lets hover reliably resolve to the actual scatter point. */}
          {trendSegment && (
            <ReferenceLine
              segment={trendSegment}
              stroke="#6b6b78"
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
            />
          )}
          <Scatter data={points} fill="#a78bfa" />
        </ScatterChart>
      </ResponsiveContainer>
      <p className="chart-caption">Each point is one region. {disclaimer}</p>
    </div>
  )
}
