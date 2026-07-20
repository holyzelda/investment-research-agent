import { describe, expect, it } from 'vitest'
import { buildTieLineMapOption } from '@/views/tie-line/components/tieLineMapOption'

const theme = {
  tooltipBackground: 'tooltip-bg',
  tooltipBorder: 'tooltip-border',
  tooltipText: 'tooltip-text',
  land: 'land',
  boundary: 'boundary',
  landHover: 'land-hover',
  station: 'station',
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

function lineSeries(chartOption) {
  return chartOption.series.filter((series) => series.type === 'lines' && series.effect)
}

describe('联络线地图 option', () => {
  it('从资料起点到终点绘制动态箭头，并保持线路与箭头同色', () => {
    const series = lineSeries(option())
    const first = series.find((item) => item.effect.color === 'runtime-800')

    expect(first.data[0].coords).toEqual([[100, 30], [110, 35]])
    expect(first.effect).toMatchObject({
      show: true,
      symbol: 'arrow',
      symbolSize: 6,
      period: 4,
      trailLength: 0,
      color: 'runtime-800',
    })
    expect(first.lineStyle.color).toBe(first.effect.color)
    expect(first.data[0]).toMatchObject({ id: 1, info: lines[0] })
  })

  it('按电压运行时颜色分组，并为未知电压采用兜底色', () => {
    const series = lineSeries(option())

    expect(series).toHaveLength(3)
    expect(series.map((item) => item.effect.color)).toEqual([
      'runtime-800', 'runtime-500', 'runtime-unknown',
    ])
  })

  it('将主要河流作为静默、无动画的低层背景，并防守无 info 的 tooltip', () => {
    const chartOption = option()
    const riverSeries = chartOption.series.find((series) => series.id === 'map-natural-rivers')

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
    })
    expect(chartOption.geo.emphasis.itemStyle).toEqual({ areaColor: 'land-hover' })
    expect(chartOption.geo.regions?.find((region) => region.name === '南海诸岛')).toBeUndefined()
  })

  it('保留选中高亮、非选中弱化和端点去重', () => {
    const chartOption = option(1)
    const selected = lineSeries(chartOption).find((item) => item.effect.color === 'runtime-800').data[0]
    const unselected = lineSeries(chartOption).find((item) => item.effect.color === 'runtime-500').data[0]
    const stations = chartOption.series.find((series) => series.type === 'scatter')

    expect(selected.lineStyle).toMatchObject({ width: 5.1, opacity: 1 })
    expect(unselected.lineStyle.opacity).toBe(0.28)
    expect(stations.data).toHaveLength(4)
  })
})
