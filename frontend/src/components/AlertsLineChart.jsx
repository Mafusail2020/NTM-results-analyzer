import { useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'

const METRICS = {
  alert_count: { label: 'Alert count', unit: '', decimals: 0, tooltipLabel: 'Alerts' },
  hours_active: { label: 'Hours active', unit: 'h', decimals: 1, tooltipLabel: 'Hours active' },
}

function CustomTooltip({ active, payload, metric }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const m = METRICS[metric]
  const value = metric === 'hours_active' ? p[metric].toFixed(1) : p[metric]
  return (
    <div className="tooltip-box">
      <div>{p.date}</div>
      <div>{m.tooltipLabel}: {value}{m.unit}</div>
    </div>
  )
}

export default function AlertsLineChart({ data, years, regionLabel, durationNote }) {
  const [metric, setMetric] = useState('alert_count')

  return (
    <div>
      <div className="toggle-group" style={{ marginBottom: 10 }}>
        {Object.entries(METRICS).map(([id, m]) => (
          <button
            key={id}
            className={`toggle-btn ${metric === id ? 'active' : ''}`}
            onClick={() => setMetric(id)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#2a2a32" vertical={false} />
          <XAxis
            dataKey="x"
            type="number"
            domain={[years[0], years[years.length - 1] + 1]}
            allowDataOverflow
            ticks={years}
            tickFormatter={(v) => Math.round(v)}
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
          />
          <YAxis stroke="#6b6b78" tick={{ fontSize: 12 }} allowDecimals={metric === 'hours_active'} />
          <Tooltip content={<CustomTooltip metric={metric} />} />
          {metric === 'hours_active' && regionLabel !== 'All Ukraine' && (
            <ReferenceLine
              y={24}
              stroke="#6b6b78"
              strokeDasharray="3 3"
              ifOverflow="extendDomain"
              label={{ value: '24h', position: 'right', fill: '#6b6b78', fontSize: 11 }}
            />
          )}
          <Line
            type="monotone"
            dataKey={metric}
            stroke="#f87171"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="chart-caption">
        {regionLabel}, {METRICS[metric].label.toLowerCase()}. Data from 2022 onward.
        {metric === 'hours_active' && (
          <>
            {regionLabel === 'All Ukraine' && ' Summed across regions, so can exceed 24h.'}
            {' '}{durationNote}
          </>
        )}
        {' '}Short time-series comparisons are weak evidence — see the correlation scatter below.
      </p>
    </div>
  )
}
