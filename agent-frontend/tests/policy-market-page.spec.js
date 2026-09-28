import { describe, expect, it } from 'vitest'
import router from '@/router'
import layoutSource from '@/layout/index.vue?raw'
import pageSource from '@/views/policy-market/index.vue?raw'
import composerSource from '@/views/policy-market/components/ConsultationComposer.vue?raw'
import pulseSource from '@/views/policy-market/components/MarketPulse.vue?raw'

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

  it('试用账号在政策咨询页显示就近额度提示，仅新建提问时出现', () => {
    expect(pageSource).toContain('<TrialQuotaNotice')
    expect(pageSource).toContain('feature="consultation"')
    expect(pageSource).toContain('useTrialQuotaStore()')
    expect(pageSource).toContain('v-if="!isReading"')
    expect(pageSource).toContain('policy-market-page__trial')
  })

  it('删除历史研究需要确认后才委托 Store 执行', () => {
    expect(pageSource).toContain('@delete="handleDeleteConsultation"')
    expect(pageSource).toContain('ElMessageBox.confirm')
    expect(pageSource).toContain("store.removeConsultation(id)")
    expect(pageSource).toContain("ElMessage.success('已删除')")
  })

  it('将页面青色强调色改为蓝色，并统一指定卡片背景为侧栏背景', () => {
    expect(pageSource).toContain('--pm-accent: var(--xc-accent-blue)')
    expect(pageSource).toContain('--pm-surface: var(--xc-surface-raised)')
    expect(composerSource).toContain('background: var(--pm-surface, var(--xc-surface-raised))')
    expect(pulseSource).toContain('background: var(--pm-surface, var(--xc-surface-card))')
    expect(pulseSource).toContain('color-mix(in srgb, var(--xc-accent-blue) 14%, transparent)')
    expect(pageSource).not.toContain('--pm-accent: #54c6d6')
    expect(pulseSource).not.toContain('rgba(84, 198, 214, .14)')
  })
})
