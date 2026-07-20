function fmtMw(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toLocaleString('zh-CN')} MW`
}

function widthOf(capacity) {
  if (!capacity) return 1.6
  return 1.6 + Math.min(capacity / 2000, 4)
}

function buildLineGroups(lines, selectedId, voltageColors, unknownColor) {
  const hasSelection = selectedId !== null && selectedId !== undefined
  const groups = new Map()

  lines.forEach((line) => {
    const color = voltageColors[line.voltageText] || unknownColor
    if (!groups.has(color)) groups.set(color, [])

    const selected = hasSelection && line.id === selectedId
    groups.get(color).push({
      id: line.id,
      name: line.name,
      coords: [
        [line.startLng, line.startLat],
        [line.endLng, line.endLat],
      ],
      lineStyle: {
        color,
        width: selected ? widthOf(line.ratedCapacityMw) + 1.5 : widthOf(line.ratedCapacityMw),
        opacity: hasSelection ? (selected ? 1 : 0.28) : 0.85,
      },
      info: line,
    })
  })

  return Array.from(groups, ([color, data]) => ({
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    lineStyle: { color, curveness: 0.18 },
    effect: {
      show: true,
      symbol: 'arrow',
      symbolSize: 6,
      period: 4,
      trailLength: 0,
      color,
    },
    emphasis: { lineStyle: { width: 4 }, focus: 'none' },
    data,
    zlevel: 2,
  }))
}

function buildPointData(lines) {
  const pointMap = new Map()
  lines.forEach((line) => {
    const add = (lng, lat, label) => {
      const key = `${lng},${lat}`
      if (!pointMap.has(key)) pointMap.set(key, { value: [lng, lat], label })
    }
    add(line.startLng, line.startLat, line.startPoint)
    add(line.endLng, line.endLat, line.endPoint)
  })
  return Array.from(pointMap.values()).map((point) => ({ value: point.value, label: point.label }))
}

function buildRiverSeries(rivers, theme) {
  const data = []
  rivers?.features?.forEach((feature) => {
    const geometry = feature?.geometry
    const segments = geometry?.type === 'LineString'
      ? [geometry.coordinates]
      : geometry?.type === 'MultiLineString'
        ? geometry.coordinates
        : []

    segments.forEach((coords) => {
      if (Array.isArray(coords) && coords.length > 1 && coords.every((point) =>
        Array.isArray(point) && Number.isFinite(point[0]) && Number.isFinite(point[1]),
      )) {
        data.push({ coords })
      }
    })
  })

  if (!data.length) return null
  return {
    id: 'map-natural-rivers',
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: true,
    silent: true,
    tooltip: { show: false },
    animation: false,
    lineStyle: { color: theme.river, width: 0.8, opacity: theme.riverOpacity },
    data,
    zlevel: 1,
    z: 2,
  }
}

// 动态箭头仅按静态线路资料的起点→终点坐标顺序运动，不表达真实潮流或功率方向。
export function buildTieLineMapOption({ lines, selectedId, voltageColors, unknownColor, theme, rivers }) {
  const riverSeries = buildRiverSeries(rivers, theme)
  const lineSeries = buildLineGroups(lines, selectedId, voltageColors, unknownColor)
  const pointData = buildPointData(lines)

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: theme.tooltipBackground,
      borderColor: theme.tooltipBorder,
      textStyle: { color: theme.tooltipText, fontSize: 12 },
      formatter: (params) => {
        if (params.seriesType === 'lines' && params.data?.info) {
          const line = params.data.info
          return [
            `<b>${line.name}</b>`,
            `${line.startPoint} → ${line.endPoint}`,
            `电压：${line.voltageText || '—'}`,
            `容量：${fmtMw(line.ratedCapacityMw)}`,
          ].join('<br/>')
        }
        if (params.seriesType === 'scatter') return params.data.label || ''
        return ''
      },
    },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.2,
      scaleLimit: { min: 1, max: 8 },
      itemStyle: {
        areaColor: theme.land,
        borderColor: theme.boundary,
        borderWidth: 0.6,
      },
      emphasis: {
        itemStyle: { areaColor: theme.landHover },
        label: { show: true, color: theme.mapLabel, fontWeight: 600 },
      },
      label: {
        show: true,
        color: theme.mapLabel,
        fontSize: 10,
      },
    },
    series: [
      ...(riverSeries ? [riverSeries] : []),
      ...lineSeries,
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        symbolSize: 4,
        itemStyle: { color: theme.station, opacity: 0.82 },
        data: pointData,
        zlevel: 3,
      },
    ],
  }
}
