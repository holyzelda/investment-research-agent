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

  it('使用轻量三栏布局，并在中窄屏依次切换为双栏和单栏', () => {
    expect(pageSource).toContain('grid-template-columns: minmax(172px, 204px) minmax(520px, 760px) minmax(260px, 304px)')
    expect(pageSource).toContain('@media (max-width: 1020px)')
    expect(pageSource).toContain('grid-template-columns: minmax(180px, 220px) minmax(0, 1fr)')
    expect(pageSource).toContain('@media (max-width: 720px)')
    expect(pageSource).toContain('grid-template-columns: 1fr')
  })

  it('页面初始化加载数据，并把操作委托给 Store', () => {
    expect(pageSource).toContain('store.loadInitialData()')
    expect(pageSource).toContain('store.startNewConsultation()')
    expect(pageSource).toContain('store.submitQuestion(question)')
    expect(pageSource).toContain('store.setStatsFilters(filters)')
  })
})
