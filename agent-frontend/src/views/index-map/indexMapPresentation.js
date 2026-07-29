export const INDEX_GRADE_META = [
  { grade: 'S', label: 'S 类·已开通', token: '--xc-map-index-s' },
  { grade: 'A', label: 'A 类·已开通', token: '--xc-map-index-a' },
  { grade: 'B', label: 'B 类·已开通', token: '--xc-map-index-b' },
  { grade: 'C', label: 'C 类·待开通', token: '--xc-map-index-c' },
]

export const INDEX_MAP_DEFAULT_ZOOM = 1.6
export const INDEX_MAP_ZOOM_LIMIT = { min: 0.78, max: 4 }

export function normalizeIndexGrade(grade) {
  if (typeof grade !== 'string') return null
  // 数据源里 A 可能细分为 A+/A-，着色时统一按 A 类处理；其余取等级首字母匹配。
  const base = grade.trim().charAt(0).toUpperCase()
  return INDEX_GRADE_META.some((item) => item.grade === base) ? base : null
}

export function buildIndexMapOption({ provinces, selectedProvinceCode, theme }) {
  const data = provinces.map((province) => {
    const selected = province.provinceCode === selectedProvinceCode
    return {
      name: province.mapName,
      value: province.indexScore,
      provinceCode: province.provinceCode,
      info: province,
      itemStyle: {
        areaColor: theme.gradeColors[normalizeIndexGrade(province.grade)] || theme.uncovered,
        borderColor: selected ? theme.selected : theme.boundary,
        borderWidth: selected ? 2.5 : 0.8,
      },
    }
  })
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
    series: [{
      type: 'map', map: 'china', roam: true, center: [104.5, 35.5], zoom: INDEX_MAP_DEFAULT_ZOOM, scaleLimit: INDEX_MAP_ZOOM_LIMIT,
      selectedMode: false,
      label: {
        show: true,
        color: theme.label,
        fontSize: 10,
        fontWeight: 600,
      },
      data,
      // 无数据省份的兜底底色与边界；有数据省份由各自 data.itemStyle 覆盖。
      itemStyle: { areaColor: theme.uncovered, borderColor: theme.boundary, borderWidth: 0.8 },
      emphasis: {
        label: { show: true, color: theme.labelActive, fontWeight: 700 },
        itemStyle: { areaColor: theme.hover, borderColor: theme.selected, borderWidth: 1.4 },
      },
    }],
  }
}
