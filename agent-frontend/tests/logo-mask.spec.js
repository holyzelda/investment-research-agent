import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const home = readFileSync(resolve(process.cwd(), 'src/views/home/index.vue'), 'utf8')
const sidebar = readFileSync(resolve(process.cwd(), 'src/layout/components/AppSidebar.vue'), 'utf8')
const logoSvg = readFileSync(resolve(process.cwd(), 'src/assets/logo.svg'), 'utf8')
const faviconSvg = readFileSync(resolve(process.cwd(), 'public/favicon.svg'), 'utf8')

describe('brand logo rendering', () => {
  it('uses the AI orb in the welcome zone and the inline SVG logo in the sidebar', () => {
    // 欢迎区已按设计对齐 trader，采用 AI 光球素材（神似）
    expect(home).toContain("import orbSrc from '@/assets/ai-sphere.png'")
    expect(home).toContain('<img class="ir-welcome__orb" :src="orbSrc" alt="" aria-hidden="true" />')
    expect(home).not.toContain("mask: url('@/assets/logo.svg')")
    // 侧栏品牌标保持内联多色 SVG，随组件样式变量着色
    expect(sidebar).toContain("import logoSvg from '@/assets/logo.svg?raw'")
    expect(sidebar).toContain('<span class="ir-sider__logo" aria-hidden="true" v-html="logoSvg" />')
    expect(sidebar).not.toContain('<img class="ir-sider__logo"')
    expect(sidebar).not.toContain("mask: url('@/assets/logo.svg')")
    expect(sidebar).toContain('--zra-icon-bg: rgba(255, 255, 255, 0.05);')
    expect(sidebar).toContain('--zra-icon-accent: #e95a4f;')
    expect(sidebar).toContain('.ir-sider__logo :deep(svg)')
  })

  it('keeps the standalone SVG fallbacks aligned with the dark theme palette', () => {
    for (const source of [logoSvg, faviconSvg]) {
      expect(source).toContain('var(--zra-icon-bg, #303234)')
      expect(source).toContain('var(--zra-icon-border, #4a4f57)')
      expect(source).toContain('var(--zra-icon-mark, #f2f4f7)')
      expect(source).toContain('var(--zra-icon-accent, #e95a4f)')
    }
  })
})
