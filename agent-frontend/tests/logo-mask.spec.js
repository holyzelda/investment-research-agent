import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const frontendRoot = process.cwd()
const logoPath = resolve(frontendRoot, 'src/assets/zq_logo.png')
const indexHtml = readFileSync(resolve(frontendRoot, 'index.html'), 'utf8')
const layout = readFileSync(resolve(frontendRoot, 'src/layout/index.vue'), 'utf8')
const sidebar = readFileSync(resolve(frontendRoot, 'src/layout/components/AppSidebar.vue'), 'utf8')

describe('brand logo rendering', () => {
  it('uses zq_logo.png for the favicon and left AppShell', () => {
    expect(existsSync(logoPath)).toBe(true)

    const logoPng = readFileSync(logoPath)
    expect(logoPng.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
    expect(logoPng[25]).toBe(6)

    expect(indexHtml).toContain('href="/src/assets/zq_logo.png" type="image/png"')
    expect(sidebar).toContain("import zqLogoUrl from '@/assets/zq_logo.png'")
    expect(sidebar).toContain('<img class="ir-shell__logo" :src="zqLogoUrl" alt="" aria-hidden="true" />')
    expect(layout).not.toContain('zq_logo.png')
    expect(sidebar).toContain('<strong>朱雀投研智能体</strong>')
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
