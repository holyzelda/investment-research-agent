import { describe, expect, it } from 'vitest'
import {
  buildReportProjectName,
  buildReportTitle,
  buildResultTitle,
  buildVersionTitle,
  formatProjectLocation,
  normalizeProjectRegion,
} from '@/utils/projectTitle'

describe('project title formatting', () => {
  it.each([
    ['浙江', '浙江省'],
    ['上海', '上海市'],
    ['深圳', '深圳市'],
    ['新疆', '新疆维吾尔自治区'],
    ['广西', '广西壮族自治区'],
    ['宁夏', '宁夏回族自治区'],
    ['西藏', '西藏自治区'],
    ['冀北', '冀北'],
    ['河北南网', '河北南网'],
    ['蒙东', '蒙东'],
    ['蒙西', '蒙西'],
    ['冀南', '冀南'],
    ['未知地区', '未知地区'],
  ])('normalizes %s to %s', (region, expected) => {
    expect(normalizeProjectRegion(region)).toBe(expected)
  })

  it.each([
    ['浙江', '浙江嘉兴站', '浙江省嘉兴站'],
    ['浙江', '浙江省嘉兴站', '浙江省嘉兴站'],
    ['浙江', '浙北嘉兴站', '浙江省浙北嘉兴站'],
    ['浙江', '浙江', '浙江省'],
    ['冀北', '冀北承德站', '冀北承德站'],
    ['甘肃', null, '甘肃省'],
  ])('formats the project location', (region, nodeName, expected) => {
    expect(formatProjectLocation(region, nodeName)).toBe(expected)
  })

  it('builds titles with the same location and scale rules', () => {
    expect(buildResultTitle('浙江', '浙江嘉兴站')).toBe('浙江省嘉兴站储能项目测算结果')
    expect(buildVersionTitle('浙江', '浙江嘉兴站', 200, 800)).toBe('测算浙江省嘉兴站 200MW/800MWh')
    expect(buildReportTitle('浙江', '浙江嘉兴站', 200, 800)).toBe('浙江省嘉兴站200MW/800MWh储能项目报告')
    expect(buildReportProjectName('浙江', '浙江嘉兴站', 200, 800)).toBe('浙江省嘉兴站200MW/800MWh独立储能项目')
  })
})
