import { describe, expect, it } from 'vitest'
import router from '@/router'
import layoutSource from '@/layout/index.vue?raw'
import pageSource from '@/views/policy-market/index.vue?raw'

describe('政策与市场页面集成', () => {
  it('注册独立政策与市场路由，并隐藏通用测算会话侧栏', () => {
    const route = router.getRoutes().find((item) => item.path === '/policy-market')

    expect(route?.name).toBe('PolicyMarket')
    expect(route?.meta?.collapseSidebar).toBe(true)
    expect(layoutSource).toContain("'/policy-market': 'policy'")
  })

  it('使用案卷式三栏布局，并在中窄屏依次切换为双栏和单栏', () => {
    expect(pageSource).toContain('grid-template-columns: minmax(196px, 228px) minmax(0, 1fr) minmax(296px, 340px)')
    expect(pageSource).toContain('width: min(100%, 1760px)')
    expect(pageSource).toContain('@media (max-width: 1280px)')
    expect(pageSource).toContain('grid-template-columns: 192px minmax(0, 1fr)')
    expect(pageSource).toContain('@media (max-width: 1100px)')
    expect(pageSource).toContain('grid-template-columns: minmax(0, 1fr)')
    expect(pageSource).toContain('@media (max-width: 640px)')
    expect(pageSource).toContain('grid-template-columns: 1fr')
  })

  it('页面初始化加载数据，并把操作委托给 Store', () => {
    expect(pageSource).toContain('store.loadInitialData()')
    expect(pageSource).toContain('store.startNewConsultation()')
    expect(pageSource).toContain('store.submitQuestion(question)')
    expect(pageSource).toContain('store.setStatsFilters(filters)')
  })

  it('新建状态显示提问器，选择历史后切换为完整案卷阅读状态', () => {
    expect(pageSource).toContain("const isReading = computed(() => store.selectedConsultationId !== null)")
    expect(pageSource).toContain('v-if="!isReading" ref="composerRef"')
    expect(pageSource).toContain('v-else class="policy-market-page__reader-bar"')
    expect(pageSource).toContain('@select="handleSelectConsultation"')
    expect(pageSource).toContain("matchMedia('(max-width: 1100px)')")
  })
})
