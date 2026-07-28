export const TIE_LINE_DEFAULT_ZOOM = 1.38
export const TIE_LINE_DEFAULT_CENTER = [104, 34]
export const TIE_LINE_LAYOUT_CENTER = ['36%', '53%']
export const TIE_LINE_LAYOUT_SIZE = '84%'
export const TIE_LINE_ZOOM_LIMIT = { min: 1, max: 8 }

function fmtMw(value) {
  return value === null || value === undefined ? '—' : `${Number(value).toLocaleString('zh-CN')} MW`
}

function widthOf(capacity) {
  if (!capacity) return 1.6
  return 1.6 + Math.min(capacity / 2000, 4)
}

function curveOf(line) {
  const seed = String(line.id ?? line.name ?? '').split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return [0.12, 0.18, 0.24][seed % 3]
}

function rhythmOf(color) {
  const seed = String(color).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return 4.6 + (seed % 4) * 0.45
}

function buildDirectionMarkerData(lines) {
  return lines.map((line) => ({
    coords: [
      [line.startLng, line.startLat],
      [line.endLng, line.endLat],
    ],
    lineStyle: { curveness: curveOf(line) },
  }))
}

function colorOf(line, voltageColors, unknownColor) {
  return voltageColors[line.voltageText] || unknownColor
}

function lineData(line, color) {
  return {
    id: line.id,
    name: line.name,
    coords: [
      [line.startLng, line.startLat],
      [line.endLng, line.endLat],
    ],
    info: line,
    color,
  }
}

function groupByColor(lines, voltageColors, unknownColor) {
  const groups = new Map()
  lines.forEach((line) => {
    const color = colorOf(line, voltageColors, unknownColor)
    if (!groups.has(color)) groups.set(color, [])
    groups.get(color).push(line)
  })
  return groups
}

function buildBaseVisualLineSeries(lines, selectedId, voltageColors, unknownColor) {
  const hasSelection = selectedId !== null && selectedId !== undefined
  const visibleLines = hasSelection ? lines.filter((line) => line.id !== selectedId) : lines

  return Array.from(groupByColor(visibleLines, voltageColors, unknownColor), ([color, group]) => ({
    id: `tie-line-visual-${color}`,
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    silent: true,
    tooltip: { show: false },
    lineStyle: { color },
    effect: {
      show: true,
      symbol: 'arrow',
      symbolSize: 7,
      period: rhythmOf(color),
      trailLength: 0,
      color,
    },
    data: group.map((line) => ({
      ...lineData(line, color),
      lineStyle: {
        color,
        width: widthOf(line.ratedCapacityMw),
        opacity: hasSelection ? 0.2 : 0.85,
        curveness: curveOf(line),
      },
    })),
    zlevel: 2,
    z: 2,
  }))
}

function buildDirectionMarkerSeries(lines, selectedId, theme) {
  const hasSelection = selectedId !== null && selectedId !== undefined
  const visibleLines = hasSelection ? lines.filter((line) => line.id !== selectedId) : lines
  return {
    id: 'tie-line-direction-markers',
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    silent: true,
    tooltip: { show: false },
    animation: false,
    lineStyle: {
      color: theme.flow,
      width: 1.2,
      opacity: hasSelection ? 0.22 : 0.72,
      curveness: 0.18,
    },
    symbol: ['none', 'arrow'],
    symbolSize: [0, hasSelection ? 5 : 7],
    effect: {
      show: true,
      symbol: 'arrow',
      symbolSize: hasSelection ? 5 : 7,
      period: 4.8,
      trailLength: 0,
      color: theme.flow,
    },
    data: buildDirectionMarkerData(visibleLines),
    zlevel: 3,
    z: 3,
  }
}

function buildLineUnderlaySeries(lines, selectedId, theme) {
  const hasSelection = selectedId !== null && selectedId !== undefined
  return {
    id: 'tie-line-underlay',
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    silent: true,
    tooltip: { show: false },
    animation: false,
    data: lines
      .filter((line) => !hasSelection || line.id !== selectedId)
      .map((line) => ({
        ...lineData(line, theme.lineUnderlay),
        lineStyle: {
          color: theme.lineUnderlay,
          width: widthOf(line.ratedCapacityMw) + 2,
          opacity: hasSelection ? 0.08 : 0.38,
          curveness: curveOf(line),
        },
      })),
    zlevel: 2,
    z: 1,
  }
}

function buildHitLineSeries(lines, voltageColors, unknownColor) {
  return Array.from(groupByColor(lines, voltageColors, unknownColor), ([color, group]) => ({
    id: `tie-line-hit-${color}`,
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    cursor: 'pointer',
    lineStyle: {
      color: 'rgba(0,0,0,0)',
      width: 12,
    },
    emphasis: {
      focus: 'none',
      lineStyle: { color, opacity: 1 },
    },
    data: group.map((line) => ({
      ...lineData(line, color),
      emphasis: {
        lineStyle: {
          color,
          width: widthOf(line.ratedCapacityMw) + 1.5,
          opacity: 1,
          curveness: curveOf(line),
        },
      },
    })),
    zlevel: 4,
    z: 1,
  }))
}

function buildSelectedLineSeries(lines, selectedId, voltageColors, unknownColor) {
  const line = lines.find((item) => item.id === selectedId)
  if (!line) return []

  const color = colorOf(line, voltageColors, unknownColor)
  return [{
    id: 'tie-line-selected-overlay',
    type: 'lines',
    coordinateSystem: 'geo',
    polyline: false,
    silent: true,
    tooltip: { show: false },
    lineStyle: { color },
    effect: {
      show: true,
      symbol: 'arrow',
      symbolSize: 10,
      period: 3.8,
      trailLength: 0,
      color: '#ffffff',
    },
    symbol: ['none', 'arrow'],
    symbolSize: [0, 10],
    data: [{
      ...lineData(line, color),
      lineStyle: {
        color,
        width: widthOf(line.ratedCapacityMw) + 1.5,
        opacity: 1,
        curveness: curveOf(line),
        shadowBlur: 10,
        shadowColor: color,
      },
    }],
    zlevel: 5,
    z: 2,
  }]
}

function buildPointData(lines, excludedCoords = new Set()) {
  const pointMap = new Map()
  lines.forEach((line) => {
    const add = (lng, lat, label) => {
      const key = `${lng},${lat}`
      if (!excludedCoords.has(key) && !pointMap.has(key)) {
        pointMap.set(key, { value: [lng, lat], label })
      }
    }
    add(line.startLng, line.startLat, line.startPoint)
    add(line.endLng, line.endLat, line.endPoint)
  })
  return Array.from(pointMap.values())
}

function buildRegularMarkerSeries(lines, selectedId, theme) {
  const selectedLine = lines.find((line) => line.id === selectedId)
  const excludedCoords = selectedLine
    ? new Set([
      `${selectedLine.startLng},${selectedLine.startLat}`,
      `${selectedLine.endLng},${selectedLine.endLat}`,
    ])
    : new Set()
  const hasSelection = Boolean(selectedLine)

  return {
    id: 'tie-line-markers-regular',
    type: 'scatter',
    coordinateSystem: 'geo',
    silent: true,
    tooltip: { show: false },
    symbolSize: 4,
    itemStyle: { color: theme.station, opacity: hasSelection ? 0.25 : 0.82 },
    data: buildPointData(lines, excludedCoords),
    zlevel: 3,
    z: 2,
  }
}

function buildSelectedMarkerSeries(lines, selectedId, voltageColors, unknownColor) {
  const line = lines.find((item) => item.id === selectedId)
  if (!line) return []

  const color = colorOf(line, voltageColors, unknownColor)
  const common = {
    type: 'scatter',
    coordinateSystem: 'geo',
    silent: true,
    tooltip: { show: false },
    itemStyle: { color },
    zlevel: 7,
    z: 2,
  }
  return [
    {
      ...common,
      id: 'tie-line-selected-start-marker',
      symbol: 'circle',
      symbolSize: 10,
      data: [{ value: [line.startLng, line.startLat], label: line.startPoint }],
    },
    {
      ...common,
      id: 'tie-line-selected-end-marker',
      symbol: 'diamond',
      symbolSize: 11,
      data: [{ value: [line.endLng, line.endLat], label: line.endPoint }],
    },
  ]
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
  const lineUnderlaySeries = buildLineUnderlaySeries(lines, selectedId, theme)
  const baseVisualSeries = buildBaseVisualLineSeries(lines, selectedId, voltageColors, unknownColor)
  const hitSeries = buildHitLineSeries(lines, voltageColors, unknownColor)
  const selectedLineSeries = buildSelectedLineSeries(lines, selectedId, voltageColors, unknownColor)
  const regularMarkerSeries = buildRegularMarkerSeries(lines, selectedId, theme)
  const selectedMarkerSeries = buildSelectedMarkerSeries(lines, selectedId, voltageColors, unknownColor)
  const directionMarkerSeries = buildDirectionMarkerSeries(lines, selectedId, theme)

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
        return ''
      },
    },
    geo: {
      map: 'china',
      roam: true,
      layoutCenter: TIE_LINE_LAYOUT_CENTER,
      layoutSize: TIE_LINE_LAYOUT_SIZE,
      center: TIE_LINE_DEFAULT_CENTER,
      zoom: TIE_LINE_DEFAULT_ZOOM,
      scaleLimit: TIE_LINE_ZOOM_LIMIT,
      tooltip: { show: false },
      itemStyle: {
        areaColor: theme.land,
        borderColor: theme.boundary,
        borderWidth: 0.6,
        shadowBlur: 10,
        shadowColor: theme.landShadow,
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
      lineUnderlaySeries,
      ...baseVisualSeries,
      regularMarkerSeries,
      directionMarkerSeries,
      ...hitSeries,
      ...selectedLineSeries,
      ...selectedMarkerSeries,
    ],
  }
}
