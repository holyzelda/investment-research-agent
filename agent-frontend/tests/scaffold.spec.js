import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import router from '@/router'
import request from '@/utils/request'

const projectRoot = resolve(import.meta.dirname, '..')

// 启动自检：登录页、默认落地对话首页、请求实例就绪
describe('frontend scaffold (platform access)', () => {
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

  it('has a login route but no register / captcha routes', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths).toContain('/login')
    expect(paths.some((p) => /register|captcha/i.test(p))).toBe(false)
    const names = router.getRoutes().map((r) => String(r.name || ''))
    expect(names.some((n) => /register|captcha|auth/i.test(n))).toBe(false)
  })

  it('defines the XC workspace elevation and responsive-content tokens', () => {
    const css = readFileSync(resolve(projectRoot, 'src/design-system/tokens.css'), 'utf8')

    for (const token of [
      '--xc-surface-workspace',
      '--xc-surface-raised',
      '--xc-surface-card',
      '--xc-surface-control',
      '--xc-border-card',
      '--xc-shadow-raised',
      '--xc-grad-atmosphere',
      '--xc-content-max',
      '--xc-content-fluid',
    ]) {
      expect(css).toContain(token)
    }
  })
})
