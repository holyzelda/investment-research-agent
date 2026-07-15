import { describe, it, expect } from 'vitest'
import router from '@/router'
import request from '@/utils/request'

// Batch 0.1 启动自检：无登录页、默认落地对话首页、请求实例就绪
describe('frontend scaffold (platform access, no login)', () => {
  it('exposes gateway base api from env', () => {
    expect(import.meta.env.VITE_APP_BASE_API).toBeTruthy()
    expect(request.defaults.baseURL).toBe(import.meta.env.VITE_APP_BASE_API)
  })

  it('lands on conversation home by default, root redirects to /home', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths).toContain('/home')
    const root = router.getRoutes().find((r) => r.path === '/')
    expect(root?.redirect).toBe('/home')
  })

  it('has NO login / register / permission-guard routes', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths.some((p) => /login|register|captcha/i.test(p))).toBe(false)
    const names = router.getRoutes().map((r) => String(r.name || ''))
    expect(names.some((n) => /login|auth/i.test(n))).toBe(false)
  })
})
