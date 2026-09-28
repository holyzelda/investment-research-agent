import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const pageSource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/index.vue'),
  'utf8',
)
const summarySource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/IndexSummaryCards.vue'),
  'utf8',
)
const rankingSource = readFileSync(
  resolve(process.cwd(), 'src/views/index-map/components/IndexRankingList.vue'),
  'utf8',
)

describe('朱雀寻龙图纵向布局', () => {
  it('为地图增加高度并压缩下方信息区', () => {
    expect(pageSource).toContain('grid-template-rows: minmax(340px, 1fr) auto auto;')
    expect(summarySource).toContain('min-height: 60px; padding: 7px 14px;')
    expect(rankingSource).toContain('padding: 9px 14px 10px;')
    expect(rankingSource).toContain('min-height: 32px; padding: 6px 11px;')
  })
})
