import { describe, expect, it } from 'vitest'
import tieLinePageSource from '@/views/tie-line/index.vue?raw'
import tieLineStatsBarSource from '@/views/tie-line/components/TieLineStatsBar.vue?raw'

const styles = tieLinePageSource.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

describe('联络线页面主体布局', () => {
  it('桌面端地图铺满页面，详情档案叠加在右侧', () => {
    expect(styles).toContain('background: var(--xc-surface-raised)')
    expect(styles).toContain('color-mix(in srgb, var(--xc-surface-raised) 72%, transparent)')
    expect(styles).toContain('.tie-line-page__body { position: absolute; inset: 0')
    expect(styles).toContain('.tie-line-page__map-wrap { position: absolute; inset: 0')
    expect(styles).toContain('.tie-line-page__detail { position: absolute')
    expect(styles).toContain('--tl-detail-width: clamp(360px, 29vw, 420px)')
    expect(styles).toContain('width: var(--tl-detail-width)')
  })

  it('右侧详情卡片与顶部统计栏共用右侧边界宽度', () => {
    expect(styles).toContain('right: var(--xc-gutter-x)')
    expect(styles).toContain('right: calc(var(--tl-detail-width) + 52px)')
    expect(tieLineStatsBarSource).toContain('width: var(--tl-detail-width, 100%)')
  })

  it('小屏切换为单列上下布局，避免横向溢出', () => {
    expect(styles).toContain('@media (max-width: 1180px)')
    expect(styles).toContain('height: 620px')
    expect(styles).toContain('top: 620px')
  })

  it('筛选无结果时在筛选栏右侧显示自动消失提示，不占用地图中央', () => {
    expect(tieLinePageSource).toContain('class="tie-line-page__notice-row"')
    expect(tieLinePageSource).toContain('v-if="showNoResultNotice"')
    expect(tieLinePageSource).toContain('tie-line-page__notice')
    expect(tieLinePageSource).toContain('window.setTimeout')
    expect(tieLinePageSource).toContain('2000')
    expect(tieLinePageSource).not.toContain('清空筛选')
    expect(tieLinePageSource).not.toContain('@click="store.resetFilters"')
    expect(styles).toContain('.tie-line-page__notice-row')
    expect(styles).not.toContain('position: absolute; top: var(--xc-space-4)')
    expect(styles).toContain('animation: tl-notice-slide')
  })

  it('有缓存时不显示整屏加载和错误态，并在挂载时静默刷新', () => {
    expect(tieLinePageSource).toContain('const isBlockingLoading = computed(() => store.loading && !store.loaded)')
    expect(tieLinePageSource).toContain('const isBlockingError = computed(() => store.error && !store.loaded)')
    expect(tieLinePageSource).toContain('v-if="isBlockingLoading"')
    expect(tieLinePageSource).toContain('v-else-if="isBlockingError"')
    expect(tieLinePageSource).toContain('store.loadLines({ force: true, silent: true })')
    expect(tieLinePageSource).toContain('store.loadLines({ force: true })')
  })
})
