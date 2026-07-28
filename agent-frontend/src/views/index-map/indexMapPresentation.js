export const INDEX_GRADE_META = [
  { grade: 'S', label: 'S 类·已开通', token: '--xc-map-index-s' },
  { grade: 'A', label: 'A 类·已开通', token: '--xc-map-index-a' },
  { grade: 'B', label: 'B 类·已开通', token: '--xc-map-index-b' },
  { grade: 'C', label: 'C 类·待开通', token: '--xc-map-index-c' },
]

export const INDEX_MAP_DEFAULT_ZOOM = 1.12
export const INDEX_MAP_ZOOM_LIMIT = { min: 0.9, max: 4 }

export function normalizeIndexGrade(grade) {
  return INDEX_GRADE_META.some((item) => item.grade === grade) ? grade : null
}

export function buildIndexMapOption({ provinces, selectedProvinceCode, theme }) {
  const data = provinces.map((province) => ({
    name: province.mapName,
    value: province.indexScore,
    provinceCode: province.provinceCode,
    info: province,
    itemStyle: { areaColor: theme.gradeColors[normalizeIndexGrade(province.grade)] || theme.uncovered },
  }))
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: theme.tooltipBackground,
      borderColor: theme.tooltipBorder,
      textStyle: { color: theme.tooltipText },
      formatter(params) {
        const info = params.data?.info
        if (!info) return ''
        const grade = normalizeIndexGrade(info.grade)
        return `<strong>${info.provinceName}</strong><br/>全国指数：${info.indexScore ?? '—'}<br/>${grade ? `${grade} 类 · 全国第 ${info.rank ?? '—'} 名` : '未覆盖'}<br/>更新时间：${info.updatedAt ?? '—'}`
      },
    },
    geo: {
      map: 'china', roam: true, zoom: INDEX_MAP_DEFAULT_ZOOM, scaleLimit: INDEX_MAP_ZOOM_LIMIT,
      itemStyle: { areaColor: theme.uncovered, borderColor: theme.boundary, borderWidth: 0.8 },
      emphasis: { itemStyle: { areaColor: theme.hover } },
      regions: selectedProvinceCode ? data.filter((item) => item.provinceCode === selectedProvinceCode).map((item) => ({
        name: item.name, itemStyle: { borderColor: theme.selected, borderWidth: 2, shadowBlur: 12, shadowColor: theme.selected },
      })) : [],
    },
    series: [{ type: 'map', geoIndex: 0, data, silent: false }],
  }
}
