import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const frontendRoot = process.cwd()
const logoPath = resolve(frontendRoot, 'public/brand-logo.svg')
const indexHtml = readFileSync(resolve(frontendRoot, 'index.html'), 'utf8')
const layout = readFileSync(resolve(frontendRoot, 'src/layout/index.vue'), 'utf8')
const sidebar = readFileSync(resolve(frontendRoot, 'src/layout/components/AppSidebar.vue'), 'utf8')

describe('brand logo rendering', () => {
  it('uses one real SVG source for the favicon, top bar, and sidebar', () => {
    expect(existsSync(logoPath)).toBe(true)

    const logoSvg = readFileSync(logoPath, 'utf8')
    expect(logoSvg).toContain('<svg')
    expect(logoSvg).toContain('viewBox="0 0 465 768"')
    expect(logoSvg).not.toContain('<image')
    expect(logoSvg).not.toMatch(/data:image\//i)

    expect(indexHtml).toContain('href="/brand-logo.svg"')
    expect(layout).toContain('src="/brand-logo.svg"')
    expect(sidebar).toContain('src="/brand-logo.svg"')
    expect(layout).toContain('<img class="ir-brand__mark" src="/brand-logo.svg" alt="" aria-hidden="true" />')
    expect(sidebar).toContain('<img class="ir-sider__logo" src="/brand-logo.svg" alt="" aria-hidden="true" />')
    expect(layout).toContain('<span class="ir-brand__name">{{ title }}</span>')
    expect(sidebar).toContain('<span class="ir-sider__brand">朱雀投研智能体</span>')
    expect(sidebar).not.toContain("import logoSvg from '@/assets/logo.svg?raw'")

    expect(existsSync(resolve(frontendRoot, 'public/favicon.svg'))).toBe(false)
    expect(existsSync(resolve(frontendRoot, 'src/assets/logo.svg'))).toBe(false)
  })

  it('keeps the welcome orb independent from the brand logo', () => {
    const home = readFileSync(resolve(frontendRoot, 'src/views/home/index.vue'), 'utf8')
    expect(home).toContain("import orbSrc from '@/assets/ai-sphere.png'")
    expect(home).toContain('<img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />')
  })
})
