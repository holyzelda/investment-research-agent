import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const homeSource = readFileSync(resolve(process.cwd(), 'src/views/home/index.vue'), 'utf8')

describe('home responsive layout', () => {
  it('keeps the laptop layout compact and removes the stacked page scroll', () => {
    const narrowStart = homeSource.indexOf('@media (max-width: 1519px)')
    const laptopStart = homeSource.indexOf('@media (min-width: 1101px) and (max-width: 1519px)')
    const narrowBlock = homeSource.slice(narrowStart, laptopStart)

    expect(narrowBlock).toContain('display: flex')
    expect(narrowBlock).toContain('min-height: 0')
    expect(narrowBlock).toContain('overflow: hidden')
    expect(narrowBlock).not.toContain('minmax(620px')
    expect(narrowBlock).not.toContain('overflow-y: auto')
  })

  it('uses a Home-only project archive drawer below 1100px', () => {
    expect(homeSource).toContain('class="ir-home__ledger-trigger"')
    expect(homeSource).toContain(':aria-expanded="projectRailOpen"')
    expect(homeSource).toContain("class=\"ir-home__side\" :class=\"{ 'is-open': projectRailOpen }\"")
    expect(homeSource).toContain("width: min(360px, calc(100vw - 32px))")
    expect(homeSource).toContain("event.key === 'Escape'")
  })

  it('preserves the large-screen project archive grid', () => {
    expect(homeSource).toContain('grid-template-columns: minmax(0, 1fr) clamp(280px, 22vw, 340px)')
    expect(homeSource).toContain('grid-template-rows: auto minmax(0, 1fr) minmax(136px, 0.48fr)')
  })
})
