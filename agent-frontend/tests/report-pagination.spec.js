import { describe, expect, it, vi } from 'vitest'
import { collectPrintUnits, paginateReportDom } from '@/views/report/utils/paginateReport'

function setHeight(element, height) {
  Object.defineProperty(element, 'scrollHeight', { configurable: true, get: () => {
    return [...element.children].reduce((sum, child) => sum + Number(child.dataset.height || 0), 0)
  } })
  element.getBoundingClientRect = () => ({ height })
}

function sourceWith(heights) {
  const source = document.createElement('div')
  const chapter = document.createElement('section')
  chapter.className = 'ir-report-section'
  heights.forEach(({ height, className = 'block', text = 'content' }) => {
    const element = document.createElement('div')
    element.className = className
    element.dataset.height = String(height)
    element.textContent = text
    chapter.appendChild(element)
  })
  source.appendChild(chapter)
  return source
}

function measuredHeight(element) {
  const own = Number(element.dataset?.height || 0)
  return own || [...element.children].reduce((sum, child) => sum + measuredHeight(child), 0)
}

function hostWithMeasuredPages(pageHeight) {
  const host = document.createElement('div')
  const originalAppend = host.appendChild.bind(host)
  vi.spyOn(host, 'appendChild').mockImplementation((page) => {
    const result = originalAppend(page)
    const content = page.firstElementChild
    Object.defineProperty(content, 'scrollHeight', { configurable: true, get: () => measuredHeight(content) })
    Object.defineProperty(content, 'clientHeight', { configurable: true, value: pageHeight })
    return result
  })
  return host
}

describe('report pagination', () => {
  it('collects chapter children in document order and marks headings', () => {
    const source = sourceWith([
      { height: 20, className: 'ir-report-chapter-heading', text: 'chapter' },
      { height: 40, text: 'body' },
    ])
    const units = collectPrintUnits(source)
    expect(units.map((unit) => unit.element.textContent)).toEqual(['chapter', 'body'])
    expect(units.map((unit) => unit.keepWithNext)).toEqual([true, false])
    expect(units.map((unit) => unit.beforeGap)).toEqual([0, 0])
  })

  it('measures source layout gaps and applies them to cloned print units', () => {
    const source = sourceWith([
      { height: 20, text: 'previous section' },
      { height: 15, className: 'ir-report-heading', text: 'section heading' },
      { height: 20, text: 'section body' },
    ])
    const elements = source.querySelectorAll(':scope > .ir-report-section > *')
    elements[0].getBoundingClientRect = () => ({ top: 0, bottom: 20 })
    elements[1].getBoundingClientRect = () => ({ top: 56, bottom: 71 })
    elements[2].getBoundingClientRect = () => ({ top: 95, bottom: 115 })

    const units = collectPrintUnits(source)
    const host = hostWithMeasuredPages(200)
    const result = paginateReportDom({ source, host, pageHeight: 200 })
    const printed = result.pages[0].querySelectorAll('.ir-report-print-unit')

    expect(units.map((unit) => unit.beforeGap)).toEqual([0, 36, 24])
    expect([...printed].map((element) => element.style.getPropertyValue('--ir-report-before-gap')))
      .toEqual(['0px', '36px', '24px'])
  })

  it('creates fixed pages without an empty trailing page', () => {
    const source = sourceWith([{ height: 60 }, { height: 40 }, { height: 20 }])
    const host = hostWithMeasuredPages(100)
    const result = paginateReportDom({ source, host, pageHeight: 100 })
    expect(result.pages).toHaveLength(2)
    expect(result.pages.map((page) => page.querySelectorAll('.block').length)).toEqual([2, 1])
    expect(result.pages.every((page) => page.firstElementChild.matches('.ir-report-print-page__content'))).toBe(true)
    expect(result.pages.map((page) => page.querySelectorAll('.ir-report-watermark__text').length)).toEqual([15, 15])
    expect(result.pages.every((page) => page.querySelector('.ir-report-watermark')?.getAttribute('aria-hidden') === 'true')).toBe(true)
    expect(result.pages.at(-1).classList.contains('ir-report-print-page--last')).toBe(true)
  })

  it('keeps the operation groups in one grid unit', () => {
    const source = document.createElement('div')
    source.innerHTML = `
      <section class="ir-report-section">
        <div class="ir-report-operation-layout" data-height="70">
          <section class="ir-report-operation-group">spot market</section>
          <section class="ir-report-operation-group">charging costs</section>
          <section class="ir-report-operation-group">actual operations</section>
        </div>
      </section>`
    const units = collectPrintUnits(source)
    expect(units).toHaveLength(1)
    expect(units[0].element.classList.contains('ir-report-operation-layout')).toBe(true)
    expect(units[0].element.querySelectorAll('.ir-report-operation-group')).toHaveLength(3)
  })

  it('keeps the revenue chart and table in one grid unit', () => {
    const source = document.createElement('div')
    source.innerHTML = `
      <section class="ir-report-section">
        <div class="ir-report-revenue-layout" data-height="70">
          <div class="ir-report-chart-card">chart</div>
          <table class="ir-report-revenue-table"><tbody><tr><td>data</td></tr></tbody></table>
        </div>
      </section>`
    const units = collectPrintUnits(source)
    expect(units).toHaveLength(1)
    expect(units[0].element.classList.contains('ir-report-revenue-layout')).toBe(true)
  })

  it('keeps a heading on the current page and splits the following table into remaining space', () => {
    const source = document.createElement('div')
    source.innerHTML = `
      <section class="ir-report-section">
        <div class="block" data-height="50">previous</div>
        <header class="ir-report-chapter-heading" data-height="15">chapter</header>
        <table class="ir-report-table">
          <thead data-height="10"><tr><th>head</th></tr></thead>
          <tbody><tr data-height="20"><td>one</td></tr><tr data-height="20"><td>two</td></tr><tr data-height="20"><td>three</td></tr></tbody>
        </table>
      </section>`
    const host = hostWithMeasuredPages(100)
    const result = paginateReportDom({ source, host, pageHeight: 100 })
    expect(result.pages[0].textContent).toContain('chapter')
    expect(result.pages[0].textContent).toContain('one')
    expect(result.pages[1].textContent).toContain('three')
  })

  it('moves a chapter heading to the next page when no following content fits', () => {
    const source = sourceWith([
      { height: 65, text: 'previous chapter' },
      { height: 15, className: 'ir-report-chapter-heading', text: 'chapter heading' },
      { height: 25, text: 'chapter body' },
    ])
    const host = hostWithMeasuredPages(100)
    const result = paginateReportDom({ source, host, pageHeight: 100 })

    expect(result.pages).toHaveLength(2)
    expect(result.pages[0].textContent).not.toContain('chapter heading')
    expect(result.pages[1].firstElementChild.textContent).toContain('chapter heading')
    expect(result.pages[1].textContent).toContain('chapter body')
  })

  it('moves a heading with its first content block', () => {
    const source = sourceWith([
      { height: 80, text: 'first' },
      { height: 15, className: 'ir-report-heading', text: 'heading' },
      { height: 20, text: 'paired' },
    ])
    const host = hostWithMeasuredPages(100)
    const result = paginateReportDom({ source, host, pageHeight: 100 })
    expect(result.pages).toHaveLength(2)
    expect(result.pages[1].textContent).toContain('heading')
    expect(result.pages[1].textContent).toContain('paired')
  })

  it('lets a splittable table fill the remaining space on the heading page instead of pushing it to the next page', () => {
    const source = document.createElement('div')
    source.innerHTML = `
      <section class="ir-report-section">
        <header class="ir-report-chapter-heading" data-height="15">chapter 4</header>
        <div class="ir-report-heading" data-height="15">4.1 heading</div>
        <p class="ir-report-intro" data-height="15">intro</p>
        <div class="ir-report-table-wrap" data-height="100">
          <table class="ir-report-boundary-table">
            <thead data-height="10"><tr><th>head</th></tr></thead>
            <tbody><tr data-height="20"><td>r1</td></tr><tr data-height="20"><td>r2</td></tr><tr data-height="20"><td>r3</td></tr></tbody>
          </table>
        </div>
      </section>`
    const host = hostWithMeasuredPages(100)
    const result = paginateReportDom({ source, host, pageHeight: 100 })
    // 大标题、小标题、引导语和表格的一部分应在同一页，而不是各自占一页
    expect(result.pages[0].textContent).toContain('chapter 4')
    expect(result.pages[0].textContent).toContain('4.1 heading')
    expect(result.pages[0].textContent).toContain('intro')
    expect(result.pages[0].textContent).toContain('r1')
  })
})
