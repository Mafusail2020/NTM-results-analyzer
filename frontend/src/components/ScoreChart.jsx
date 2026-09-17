import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'

const METRIC_LABEL = {
  avg: 'Average score',
  min: 'Min score',
  max: 'Max score',
  total_students: 'Total students',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tooltip-box">
      <div>{label}</div>
      <div>{payload[0].name}: {payload[0].value}</div>
    </div>
  )
}

// Dots pop in left-to-right (scaling up from 0), staggered so the last
// point lands around when the line's own draw-in animation finishes.
function makeAnimatedDot(pointCount) {
  return function AnimatedDot({ cx, cy, index }) {
    if (cx == null || cy == null) return null
    const delay = pointCount > 1 ? (index / (pointCount - 1)) * 0.5 : 0
    return (
      <circle
        key={`dot-${index}`}
        cx={cx}
        cy={cy}
        fill="#a78bfa"
        style={{
          animation: 'score-dot-pop 0.22s cubic-bezier(0.2, 0.8, 0.3, 1) both',
          animationDelay: `${delay}s`,
        }}
      />
    )
  }
}

export default function ScoreChart({ data, metric, regionLabel, subjectLabel, years }) {
  if (!data.length) {
    return <p className="empty-note">No score data for this selection.</p>
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#2a2a32" vertical={false} />
          <XAxis
            dataKey="year"
            type="number"
            domain={[years[0], years[years.length - 1] + 1]}
            allowDataOverflow
            ticks={years}
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            stroke="#6b6b78"
            tick={{ fontSize: 12 }}
            domain={metric === 'total_students' ? ['auto', 'auto'] : [100, 200]}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey={metric}
            name={METRIC_LABEL[metric]}
            stroke="#a78bfa"
            strokeWidth={2.5}
            dot={makeAnimatedDot(data.length)}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="chart-caption">
        {metric === 'total_students'
          ? `${METRIC_LABEL[metric]} for ${regionLabel}, any subject.`
          : `${METRIC_LABEL[metric]} for ${regionLabel} — ${subjectLabel}. Scale: 100–200.`}
      </p>
    </div>
  )
}
