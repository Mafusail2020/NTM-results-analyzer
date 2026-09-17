import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'

const SCALE_FLOOR = 100

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="tooltip-box">
      <div>{label}</div>
      <div>Male avg: {p.male_avg ?? '—'}</div>
      <div>Female avg: {p.female_avg ?? '—'}</div>
    </div>
  )
}

export default function GenderPyramidChart({ data, regionLabel, subjectLabel }) {
  if (!data.length) {
    return <p className="empty-note">No score data for this selection.</p>
  }

  // Diverging bars measure distance above the scale floor (100), not the
  // raw score, so the chart uses its full width to show the male/female
  // gap instead of mostly-empty bars over a 100-200 scale. Axis ticks are
  // converted back to real scores.
  const chartData = data.map((r) => ({
    year: r.year,
    male_avg: r.male_avg,
    female_avg: r.female_avg,
    male_delta: r.male_avg != null ? -(r.male_avg - SCALE_FLOOR) : null,
    female_delta: r.female_avg != null ? r.female_avg - SCALE_FLOOR : null,
  }))

  return (
    <div>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart
          data={chartData}
          layout="vertical"
          stackOffset="sign"
          margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
          barCategoryGap={1}
        >
          <CartesianGrid stroke="#2a2a32" horizontal={false} />
          <XAxis
            type="number"
            domain={[-100, 100]}
            ticks={[-100, -50, 0, 50, 100]}
            tickFormatter={(v) => SCALE_FLOOR + Math.abs(v)}
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
          />
          <YAxis type="category" dataKey="year" stroke="#6b6b78" tick={{ fontSize: 12 }} width={44} />
          <ReferenceLine x={0} stroke="#34343e" />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="male_delta" name="Male" fill="#60a5fa" stackId="pyramid" />
          <Bar dataKey="female_delta" name="Female" fill="#f472b6" stackId="pyramid" />
        </BarChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: 16, marginTop: 4, fontSize: 12 }}>
        <span style={{ color: '#60a5fa' }}>■ male</span>
        <span style={{ color: '#f472b6' }}>■ female</span>
      </div>
      <p className="chart-caption">
        Average score by gender, {regionLabel} — {subjectLabel}. Bar length is distance above
        the scale floor (100), not the raw score, so a small overall change stays visible.
      </p>
    </div>
  )
}
