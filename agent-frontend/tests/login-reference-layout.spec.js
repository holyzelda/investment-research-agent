import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const projectRoot = resolve(import.meta.dirname, '..')
const loginSource = readFileSync(resolve(projectRoot, 'src/views/login.vue'), 'utf8')

describe('province chooser reference login layout', () => {
  it('uses the reference capability and quick-entry composition', () => {
    expect(loginSource).toContain('class="capability-card glass-card"')
    expect(loginSource).toContain('class="capability-grid"')
    expect(loginSource).toContain('class="quick-card glass-card"')
    expect(loginSource).toContain('class="quick-grid"')
    expect(loginSource).toContain("title: '全流程交易辅助'")
    expect(loginSource).toContain("title: 'AI 智能决策引擎'")
    expect(loginSource).toContain("title: '新手引导'")
    expect(loginSource).toContain("title: '产品文档'")
    expect(loginSource).not.toContain('class="market-card glass-card"')
    expect(loginSource).not.toContain('class="notice-card glass-card"')
  })

  it('keeps the project login flow and delegates captcha interaction', () => {
    expect(loginSource).toContain('await session.login(form)')
    expect(loginSource).toContain('clearLoginRequired()')
    expect(loginSource).toContain('permission.resetRoutes()')
    expect(loginSource).toContain('await session.loadUserInfo({ force: true })')
    expect(loginSource).toContain("router.push(route.query.redirect || '/home')")
    expect(loginSource).toContain('@submit.prevent="onLogin"')
    expect(loginSource).toContain('<GraphicalCaptcha')
    expect(loginSource).toContain('@verified="onCaptchaVerified"')
  })
})
