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

  it('使用三栏布局并在窄屏切换为单列', () => {
    expect(pageSource).toContain('grid-template-columns: 248px minmax(0, 1fr) 336px')
    expect(pageSource).toContain('@media (max-width: 1180px)')
    expect(pageSource).toContain('grid-template-columns: 1fr')
  })

  it('页面初始化加载数据，并把操作委托给 Store', () => {
    expect(pageSource).toContain('store.loadInitialData()')
    expect(pageSource).toContain('store.startNewConsultation()')
    expect(pageSource).toContain('store.submitQuestion(question)')
    expect(pageSource).toContain('store.setStatsFilters(filters)')
  })
})
