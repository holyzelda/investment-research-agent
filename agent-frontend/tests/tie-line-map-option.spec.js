import { describe, expect, it } from 'vitest'
import {
  TIE_LINE_DEFAULT_ZOOM,
  TIE_LINE_ZOOM_LIMIT,
  buildTieLineMapOption,
} from '@/views/tie-line/components/tieLineMapOption'

const theme = {
  tooltipBackground: 'tooltip-bg',
  tooltipBorder: 'tooltip-border',
  tooltipText: 'tooltip-text',
  land: 'land',
  boundary: 'boundary',
  landHover: 'land-hover',
  station: 'station',
  lineUnderlay: 'line-underlay',
  flow: 'flow',
  landShadow: 'land-shadow',
}

const lines = [
  {
    id: 1, name: '甲乙线', startPoint: '甲站', endPoint: '乙站',
    startLng: 100, startLat: 30, endLng: 110, endLat: 35,
    voltageText: '±800 kV', ratedCapacityMw: 4000,
  },
  {
    id: 2, name: '乙丙线', startPoint: '乙站', endPoint: '丙站',
    startLng: 110, startLat: 35, endLng: 120, endLat: 32,
    voltageText: '500 kV', ratedCapacityMw: 1000,
  },
  {
    id: 3, name: '丙丁线', startPoint: '丙站', endPoint: '丁站',
    startLng: 120, startLat: 32, endLng: 121, endLat: 28,
    voltageText: '待核实', ratedCapacityMw: null,
  },
]

const rivers = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', geometry: { type: 'LineString', coordinates: [[90, 30], [100, 31]] } },
    { type: 'Feature', geometry: { type: 'MultiLineString', coordinates: [[[100, 31], [110, 30]], [[110, 30], [120, 29]]] } },
    { type: 'Feature', geometry: { type: 'Point', coordinates: [100, 30] } },
  ],
}

function option(selectedId = null) {
  return buildTieLineMapOption({
    lines,
    selectedId,
    voltageColors: { '±800 kV': 'runtime-800', '500 kV': 'runtime-500' },
    unknownColor: 'runtime-unknown',
    rivers,
    theme: { ...theme, river: 'runtime-river', riverOpacity: 0.48 },
  })
}

function seriesById(chartOption, id) {
  return chartOption.series.find((series) => series.id === id)
}

function visualSeries(chartOption) {
  return chartOption.series.filter((series) => series.id.startsWith('tie-line-visual-'))
}

function hitSeries(chartOption) {
  return chartOption.series.filter((series) => series.id.startsWith('tie-line-hit-'))
}

describe('联络线地图 option', () => {
  it('使用共享的全国视图缩放常量', () => {
    const chartOption = option()

    expect(chartOption.geo.zoom).toBe(TIE_LINE_DEFAULT_ZOOM)
    expect(chartOption.geo.scaleLimit).toEqual(TIE_LINE_ZOOM_LIMIT)
  })

  it('保持视觉线宽，同时以透明命中层扩大点击热区并承接悬停', () => {
    const chartOption = option()
    const visual = visualSeries(chartOption).find((series) => series.effect.color === 'runtime-800')
    const hit = hitSeries(chartOption).find((series) => series.emphasis.lineStyle.color === 'runtime-800')

    expect(visual.data[0]).toMatchObject({
      id: 1,
      coords: [[100, 30], [110, 35]],
      lineStyle: { width: 3.6, opacity: 0.85, curveness: 0.18 },
    })
    expect(visual.effect).toMatchObject({
      show: true,
      symbol: 'arrow',
      symbolSize: 7,
      trailLength: 0,
      color: 'runtime-800',
    })
    expect(hit).not.toHaveProperty('effect')
    expect(hit).toMatchObject({
      cursor: 'pointer',
      lineStyle: { color: 'rgba(0,0,0,0)', width: 12 },
      emphasis: { focus: 'none', lineStyle: { color: 'runtime-800', opacity: 1 } },
    })
    expect(hit.data[0]).toMatchObject({
      id: 1,
      coords: visual.data[0].coords,
      info: lines[0],
      emphasis: { lineStyle: { color: 'runtime-800', width: 5.1, opacity: 1 } },
    })
  })

  it('为彩色线路增加独立暗色衬线，并通过轻微曲率差降低重叠感', () => {
    const chartOption = option()
    const underlay = seriesById(chartOption, 'tie-line-underlay')

    expect(underlay).toMatchObject({
      silent: true,
      animation: false,
      tooltip: { show: false },
    })
    expect(underlay.data).toHaveLength(3)
    expect(underlay.data[0].lineStyle).toMatchObject({
      color: 'line-underlay',
      width: 5.6,
      opacity: 0.38,
      curveness: 0.18,
    })
    expect(new Set(underlay.data.map((line) => line.lineStyle.curveness)).size).toBeGreaterThan(1)
  })

  it('使用统一高对比终点箭头表达方向，不让方向依赖线路颜色', () => {
    const chartOption = option()
    const markers = seriesById(chartOption, 'tie-line-direction-markers')
    const visual = visualSeries(chartOption).find((series) => series.effect.color === 'runtime-800')
    const direction = seriesById(chartOption, 'tie-line-direction-markers')

    expect(markers).toMatchObject({
      silent: true,
      animation: false,
      symbol: ['none', 'arrow'],
      symbolSize: [0, 7],
      lineStyle: { color: 'flow', opacity: 0.72 },
      effect: { color: 'flow', symbol: 'arrow' },
    })
    expect(direction.data[0].coords).toEqual([
      [lines[0].startLng, lines[0].startLat],
      [lines[0].endLng, lines[0].endLat],
    ])
    expect(visual.effect).toMatchObject({
      symbol: 'arrow',
      symbolSize: 7,
      color: 'runtime-800',
    })
  })

  it('按电压运行时颜色分组，并为未知电压采用兜底色', () => {
    const chartOption = option()

    expect(visualSeries(chartOption)).toHaveLength(3)
    expect(visualSeries(chartOption).map((series) => series.effect.color)).toEqual([
      'runtime-800', 'runtime-500', 'runtime-unknown',
    ])
    expect(hitSeries(chartOption)).toHaveLength(3)
  })

  it('将主要河流作为静默、无动画的低层背景，并防守无 info 的 tooltip', () => {
    const chartOption = option()
    const riverSeries = seriesById(chartOption, 'map-natural-rivers')

    expect(riverSeries).toMatchObject({
      type: 'lines',
      polyline: true,
      silent: true,
      tooltip: { show: false },
      animation: false,
      zlevel: 1,
      lineStyle: { color: 'runtime-river', opacity: 0.48 },
    })
    expect(riverSeries.data).toHaveLength(3)
    expect(chartOption.tooltip.formatter({ seriesType: 'lines', data: riverSeries.data[0] })).toBe('')
  })

  it('默认显示南海诸岛并继承地图主题样式', () => {
    const chartOption = option()

    expect(chartOption.geo.itemStyle).toMatchObject({
      areaColor: 'land',
      borderColor: 'boundary',
      borderWidth: 0.6,
      shadowBlur: 10,
      shadowColor: 'land-shadow',
    })
    expect(chartOption.geo.emphasis.itemStyle).toEqual({ areaColor: 'land-hover' })
    expect(chartOption.geo.tooltip).toEqual({ show: false })
    expect(chartOption.geo.regions?.find((region) => region.name === '南海诸岛')).toBeUndefined()
  })

  it('选中线路置顶、弱化其他线路并使用差异化端点标记', () => {
    const chartOption = option(1)
    const base = visualSeries(chartOption)
    const overlay = seriesById(chartOption, 'tie-line-selected-overlay')
    const regularMarkers = seriesById(chartOption, 'tie-line-markers-regular')
    const startMarker = seriesById(chartOption, 'tie-line-selected-start-marker')
    const endMarker = seriesById(chartOption, 'tie-line-selected-end-marker')

    expect(base.flatMap((series) => series.data).map((line) => line.id)).toEqual([2, 3])
    expect(base.flatMap((series) => series.data).every((line) => line.lineStyle.opacity === 0.2)).toBe(true)
    expect(overlay).toMatchObject({
      silent: true,
      tooltip: { show: false },
      zlevel: 5,
      effect: { color: '#ffffff' },
      data: [{ id: 1, lineStyle: { width: 5.1, opacity: 1, shadowBlur: 10 } }],
    })
    expect(regularMarkers).toMatchObject({
      silent: true,
      tooltip: { show: false },
      itemStyle: { opacity: 0.25 },
    })
    expect(regularMarkers.data).toHaveLength(2)
    expect(startMarker).toMatchObject({
      symbol: 'circle',
      symbolSize: 10,
      itemStyle: { color: 'runtime-800' },
      data: [{ value: [100, 30] }],
      zlevel: 7,
      silent: true,
    })
    expect(endMarker).toMatchObject({
      symbol: 'diamond',
      symbolSize: 11,
      itemStyle: { color: 'runtime-800' },
      data: [{ value: [110, 35] }],
      zlevel: 7,
      silent: true,
    })
  })
})
