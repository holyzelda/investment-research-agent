import { describe, expect, it } from 'vitest'
import { INDEX_GRADE_META, INDEX_MAP_ZOOM_LIMIT, buildIndexMapOption, normalizeIndexGrade } from '@/views/index-map/indexMapPresentation'

const province = { provinceCode: 'NMG', provinceName: '蒙西', mapName: '内蒙古', indexScore: 95, grade: 'S', rank: 1, updatedAt: '2026-07-28' }
const theme = { tooltipBackground: 'bg', tooltipBorder: 'border', tooltipText: 'text', boundary: 'boundary', uncovered: 'uncovered', hover: 'hover', selected: 'selected', gradeColors: { S: 's', A: 'a', B: 'b', C: 'c' } }

describe('全国指数地图表达', () => {
  it('将 S/A/B/C 映射到固定等级，并将非法等级归为未覆盖', () => {
    expect(normalizeIndexGrade('S')).toBe('S')
    expect(normalizeIndexGrade('A')).toBe('A')
    expect(normalizeIndexGrade('C')).toBe('C')
    expect(normalizeIndexGrade('X')).toBeNull()
    expect(INDEX_GRADE_META.map((item) => item.grade)).toEqual(['S', 'A', 'B', 'C'])
    // 河北为已开通 C 类，四档统一为“X 类·已开通”，C 类不再标注“待开通”。
    expect(INDEX_GRADE_META.every((item) => item.label.endsWith('·已开通'))).toBe(true)
    expect(INDEX_GRADE_META.find((item) => item.grade === 'C').label).toBe('C 类·已开通')
  })

  it('C 类省份使用 C 色着色，tooltip 显示分数与等级排名', () => {
    const hebei = { provinceCode: 'HE', provinceName: '河北', mapName: '河北省', indexScore: 66, grade: 'C', rank: 10, updatedAt: '2026-07-28' }
    const option = buildIndexMapOption({ provinces: [hebei], selectedProvinceCode: null, theme })
    expect(option.series[0].data[0].itemStyle.areaColor).toBe('c')
    const text = option.tooltip.formatter({ data: option.series[0].data[0] })
    expect(text).toContain('河北')
    expect(text).toContain('66')
    expect(text).toContain('C 类 · 全国第 10 名')
  })

  it('无等级区域回退到未覆盖底色', () => {
    const other = { provinceCode: 'XX', provinceName: '某省', mapName: '某省', indexScore: null, grade: null, rank: null, updatedAt: '2026-07-28' }
    const option = buildIndexMapOption({ provinces: [other], selectedProvinceCode: null, theme })
    expect(option.series[0].data[0].itemStyle.areaColor).toBe('uncovered')
    const text = option.tooltip.formatter({ data: option.series[0].data[0] })
    expect(text).toContain('未覆盖')
  })

  it('tooltip 只输出省份、指数、等级排名、更新时间', () => {
    const option = buildIndexMapOption({ provinces: [province], selectedProvinceCode: 'NMG', theme })
    const text = option.tooltip.formatter({ data: option.series[0].data[0] })
    expect(text).toContain('蒙西')
    expect(text).toContain('95')
    expect(text).toContain('全国第 1 名')
    expect(text).toContain('2026-07-28')
    expect(text).not.toContain('annualizedReturn')
    expect(option.series[0].scaleLimit).toEqual(INDEX_MAP_ZOOM_LIMIT)
  })
})
