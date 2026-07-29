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
