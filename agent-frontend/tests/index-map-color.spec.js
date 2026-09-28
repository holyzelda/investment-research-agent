import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const chinaIndexMapSource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/ChinaIndexMap.vue'),
  'utf8',
)
const provinceIndexDetailSource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/ProvinceIndexDetail.vue'),
  'utf8',
)

describe('朱雀寻龙图卡片背景', () => {
  it('地图左下角图例与装机结构小卡片使用一致背景', () => {
    expect(chinaIndexMapSource).toContain(
      '.china-index-map__legend { position: absolute; z-index: 3; left: 12px; bottom: 12px; display: flex; flex-wrap: wrap; gap: 7px 12px; max-width: calc(100% - 24px); padding: 8px 10px; box-sizing: border-box; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: rgba(255, 255, 255, 0.018);',
    )
    expect(provinceIndexDetailSource).toContain('.province-detail__capacity { --capacity-color: #54c6d6;')
    expect(provinceIndexDetailSource).toContain('border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 10px; background: rgba(255, 255, 255, 0.018);')
  })
})
