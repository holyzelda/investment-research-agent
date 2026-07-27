import { describe, expect, it } from 'vitest'
import tieLinePageSource from '@/views/tie-line/index.vue?raw'

const styles = tieLinePageSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

describe('联络线页面主体布局', () => {
  it('桌面端使用地图主体和 380-440px 右侧详情栏', () => {
    expect(styles).toContain('grid-template-columns: minmax(680px, 1fr) clamp(380px, 31vw, 440px)')
    expect(styles).toContain('gap: 18px')
  })

  it('小屏切换为单列上下布局，避免横向溢出', () => {
    expect(styles).toContain('@media (max-width: 1180px)')
    expect(styles).toContain('grid-template-columns: 1fr')
    expect(styles).toContain('min-height: 520px')
  })

  it('筛选无结果时在筛选栏右侧显示自动消失提示，不占用地图中央', () => {
    expect(tieLinePageSource).toContain('class="tie-line-page__filter-row"')
    expect(tieLinePageSource).toContain('v-if="showNoResultNotice"')
    expect(tieLinePageSource).toContain('tie-line-page__notice')
    expect(tieLinePageSource).toContain('window.setTimeout')
    expect(tieLinePageSource).toContain('2000')
    expect(tieLinePageSource).not.toContain('清空筛选')
    expect(tieLinePageSource).not.toContain('@click="store.resetFilters"')
    expect(styles).toContain('.tie-line-page__filter-row')
    expect(styles).toContain('grid-template-columns: minmax(0, 1fr) auto')
    expect(styles).not.toContain('position: absolute; top: var(--xc-space-4)')
    expect(styles).toContain('animation: tl-notice-slide')
  })
})
