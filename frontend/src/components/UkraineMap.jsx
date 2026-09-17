import { useEffect, useMemo, useState } from 'react'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { geoMercator } from 'd3-geo'

const GEO_URL = '/ukraine-oblasts.geojson'
const WIDTH = 520
const HEIGHT = 380

const GEO_TRANSITION = 'fill 0.35s ease, fill-opacity 0.35s ease, stroke 0.35s ease, stroke-width 0.35s ease'

function colorForValue(value, min, max) {
  if (value === null || value === undefined) return '#2a2a34'
  if (max === min) return '#5b3fa8'
  const t = (value - min) / (max - min)
  const from = [42, 42, 52]
  const to = [139, 92, 246]
  const rgb = from.map((c, i) => Math.round(c + (to[i] - c) * t))
  return `rgb(${rgb.join(',')})`
}

export default function UkraineMap({ regions, metricByRegion, metricLabel, selectedRegion, onSelect }) {
  const [geoData, setGeoData] = useState(null)

  useEffect(() => {
    fetch(GEO_URL)
      .then((r) => r.json())
      .then(setGeoData)
  }, [])

  const projection = useMemo(() => {
    if (!geoData) return null
    return geoMercator().fitSize([WIDTH, HEIGHT], geoData)
  }, [geoData])

  const isoToRegionId = useMemo(() => {
    const m = {}
    regions.forEach((r) => { m[r.iso] = r.id })
    return m
  }, [regions])

  const values = Object.values(metricByRegion).filter((v) => v !== null && v !== undefined)
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0

  if (!geoData || !projection) {
    return <p className="loading">Loading map…</p>
  }

  return (
    <div className="map-wrap">
      <ComposableMap
        projection={projection}
        width={WIDTH}
        height={HEIGHT}
        style={{ width: '100%', height: 'auto' }}
      >
        <Geographies geography={geoData}>
          {({ geographies }) => {
            // Draw the selected region last so its highlighted stroke isn't
            // partially painted over by a neighboring (unselected) region's
            // own stroke along their shared border.
            const ordered = [...geographies].sort((a, b) => {
              const aSel = isoToRegionId[a.properties.shapeISO] === selectedRegion
              const bSel = isoToRegionId[b.properties.shapeISO] === selectedRegion
              return Number(aSel) - Number(bSel)
            })
            return ordered.map((geo) => {
              const iso = geo.properties.shapeISO
              const regionId = isoToRegionId[iso]
              const value = regionId ? metricByRegion[regionId] : undefined
              const isSelected = regionId && regionId === selectedRegion
              const isKnown = Boolean(regionId)
              const isDimmed = Boolean(selectedRegion) && !isSelected
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onClick={() => isKnown && onSelect(regionId)}
                  style={{
                    default: {
                      fill: colorForValue(value, min, max),
                      fillOpacity: isDimmed ? 0.5 : 1,
                      stroke: isSelected ? '#a78bfa' : '#0f0f13',
                      strokeWidth: isSelected ? 2 : 0.6,
                      outline: 'none',
                      cursor: isKnown ? 'pointer' : 'default',
                      transition: GEO_TRANSITION,
                    },
                    hover: {
                      fill: isKnown ? '#8b5cf6' : colorForValue(value, min, max),
                      fillOpacity: 1,
                      stroke: '#a78bfa',
                      strokeWidth: 1.2,
                      outline: 'none',
                      cursor: isKnown ? 'pointer' : 'default',
                      transition: GEO_TRANSITION,
                    },
                    pressed: {
                      fill: '#7c3aed',
                      fillOpacity: 1,
                      stroke: '#a78bfa',
                      strokeWidth: 1.5,
                      outline: 'none',
                      transition: GEO_TRANSITION,
                    },
                  }}
                />
              )
            })
          }}
        </Geographies>
      </ComposableMap>
      <div className="map-legend">
        <span>{metricLabel}</span>
        <div className="map-legend-gradient" />
        <span>low → high</span>
      </div>
    </div>
  )
}
