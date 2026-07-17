import { describe, expect, it } from 'vitest'
import { buildVoltagePresentation, parseVoltageKv } from '@/views/tie-line/voltagePresentation'

describe('联络线电压展示', () => {
  it('解析直流和交流电压文本', () => {
    expect(parseVoltageKv('±800 kV')).toBe(800)
    expect(parseVoltageKv('1000kV')).toBe(1000)
    expect(parseVoltageKv('500 kV')).toBe(500)
    expect(parseVoltageKv('未标注')).toBeNull()
  })

  it('按额定 kV 从高到低输出图例，并建立固定暖色阶映射', () => {
    const presentation = buildVoltagePresentation(['500 kV', '±800 kV', '1000kV', '±660 kV', '220 kV'])

    expect(presentation.legendItems.map((item) => item.text)).toEqual([
      '1000kV', '±800 kV', '±660 kV', '500 kV', '220 kV',
    ])
    expect(presentation.legendItems.map((item) => item.token)).toEqual([
      '--xc-map-voltage-5', '--xc-map-voltage-4', '--xc-map-voltage-3',
      '--xc-map-voltage-2', '--xc-map-voltage-1',
    ])
    expect(presentation.tokenByText['±800 kV']).toBe('--xc-map-voltage-4')
  })

  it('为无法解析的电压采用中性兜底色，并排在标准等级后', () => {
    const presentation = buildVoltagePresentation(['500 kV', '待核实', ''])

    expect(presentation.legendItems.map((item) => item.text)).toEqual(['500 kV', '待核实'])
    expect(presentation.tokenByText.待核实).toBe('--xc-map-voltage-unknown')
  })
})
