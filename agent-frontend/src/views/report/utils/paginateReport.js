import { createReportWatermark } from './reportWatermark'

const DEFAULT_TOLERANCE = 1

function heightOf(element) {
  return element.getBoundingClientRect().height
}

function fits(container, limit, tolerance) {
  return container.scrollHeight <= limit + tolerance
}

function cloneTableShell(table) {
  const clone = table.cloneNode(false)
  const colgroup = table.querySelector(':scope > colgroup')
  const thead = table.querySelector(':scope > thead')
  if (colgroup) clone.appendChild(colgroup.cloneNode(true))
  if (thead) clone.appendChild(thead.cloneNode(true))
  const body = document.createElement('tbody')
  clone.appendChild(body)
  return { table: clone, body }
}

function applyBeforeGap(element, gap) {
  element.classList.add('ir-report-print-unit')
  element.style.setProperty('--ir-report-before-gap', `${Math.max(0, gap)}px`)
  return element
}

function keepWithNextProbe(unit) {
  if (!unit.element.matches('table')) {
    return applyBeforeGap(unit.element.cloneNode(true), unit.beforeGap)
  }
  const fragment = cloneTableShell(unit.element)
  // 对于可拆分的表格（boundary/policy/financial），探测前3行以更准确估算高度
  const canSplit = unit.element.matches('.ir-report-boundary-table, .ir-report-policy-table, .ir-report-financial-table')
  const rowLimit = canSplit ? 3 : 1
  const rows = unit.element.querySelectorAll(':scope > tbody > tr')
  for (let i = 0; i < Math.min(rows.length, rowLimit); i++) {
    fragment.body.appendChild(rows[i].cloneNode(true))
  }
  return applyBeforeGap(fragment.table, unit.beforeGap)
}

function keepWithNextProbes(units, startIndex) {
  const probes = []
  let hasSplittableTable = false
  for (let index = startIndex; index < units.length; index += 1) {
    const unit = units[index]
    probes.push(keepWithNextProbe(unit))
    // 检查是否包含可拆分的表格
    if (unit.element.matches('table.ir-report-boundary-table, table.ir-report-policy-table, table.ir-report-financial-table')) {
      hasSplittableTable = true
    }
    if (!unit.keepWithNext) {
      // 即使当前单元没有 keepWithNext，也要再看一眼下一个单元是否是可拆分表格
      const nextUnit = units[index + 1]
      if (nextUnit && nextUnit.element.matches('table.ir-report-boundary-table, table.ir-report-policy-table, table.ir-report-financial-table')) {
        hasSplittableTable = true
      }
      break
    }
  }
  return { probes, hasSplittableTable }
}

function splitTextElement(element, createPage, limit, tolerance) {
  const text = element.textContent || ''
  if (!text) return false

  let offset = 0
  while (offset < text.length) {
    const page = createPage()
    let low = 1
    let high = text.length - offset
    let accepted = 0
    let acceptedNode = null

    while (low <= high) {
      const size = Math.floor((low + high) / 2)
      const candidate = element.cloneNode(false)
      candidate.textContent = text.slice(offset, offset + size)
      page.content.appendChild(candidate)
      if (fits(page.content, limit, tolerance)) {
        accepted = size
        acceptedNode = candidate
        low = size + 1
      } else {
        candidate.remove()
        high = size - 1
      }
    }

    if (!acceptedNode) return false
    for (const child of [...page.content.children]) {
      if (child !== acceptedNode) child.remove()
    }
    offset += accepted
  }
  return true
}

function splitTable(table, current, createPage, limit, tolerance, beforeGap = 0) {
  const rows = [...table.querySelectorAll(':scope > tbody > tr')]
  if (!rows.length) return null

  let page = current
  let fragment = cloneTableShell(table)
  applyBeforeGap(fragment.table, beforeGap)
  page.content.appendChild(fragment.table)

  for (const sourceRow of rows) {
    const row = sourceRow.cloneNode(true)
    fragment.body.appendChild(row)
    if (fits(page.content, limit, tolerance)) continue

    row.remove()
    if (!fragment.body.children.length) {
      fragment.table.remove()
      if (page.content.children.length) page = createPage()
      fragment = cloneTableShell(table)
      applyBeforeGap(fragment.table, 0)
      page.content.appendChild(fragment.table)
      fragment.body.appendChild(row)
      if (!fits(page.content, limit, tolerance)) return null
      continue
    }

    page = createPage()
    fragment = cloneTableShell(table)
    applyBeforeGap(fragment.table, 0)
    page.content.appendChild(fragment.table)
    fragment.body.appendChild(row)
    if (!fits(page.content, limit, tolerance)) return null
  }
  return page
}

function splitAnalysis(analysis, createPage, limit, tolerance) {
  const header = analysis.querySelector(':scope > header')
  const rule = analysis.querySelector(':scope > .ir-report-ai-analysis__rule')
  const body = analysis.querySelector(':scope > .ir-report-ai-analysis__body')
  if (!body) return false

  let page = createPage()
  let fragment = analysis.cloneNode(false)
  if (header) fragment.appendChild(header.cloneNode(true))
  if (rule) fragment.appendChild(rule.cloneNode(true))
  let fragmentBody = body.cloneNode(false)
  fragment.appendChild(fragmentBody)
  page.content.appendChild(fragment)

  for (const sourceBlock of [...body.children]) {
    const block = sourceBlock.cloneNode(true)
    fragmentBody.appendChild(block)
    if (fits(page.content, limit, tolerance)) continue

    block.remove()
    page = createPage()
    fragment = analysis.cloneNode(false)
    fragment.classList.add('ir-report-ai-analysis--continued')
    fragmentBody = body.cloneNode(false)
    fragment.appendChild(fragmentBody)
    page.content.appendChild(fragment)
    fragmentBody.appendChild(block)

    if (fits(page.content, limit, tolerance)) continue
    block.remove()
    if (!splitTextElement(sourceBlock, createPage, limit, tolerance)) return false
    page = createPage()
    fragment = analysis.cloneNode(false)
    fragment.classList.add('ir-report-ai-analysis--continued')
    fragmentBody = body.cloneNode(false)
    fragment.appendChild(fragmentBody)
    page.content.appendChild(fragment)
  }
  return true
}

function measuredGap(previous, current) {
  if (!previous) return 0
  const previousRect = previous.getBoundingClientRect()
  const currentRect = current.getBoundingClientRect()
  return Math.max(0, currentRect.top - previousRect.bottom)
}

export function collectPrintUnits(source) {
  const units = []
  const append = (element) => {
    const expands = element.matches('.ir-report-model-section')
    if (expands) {
      for (const child of element.children) append(child)
      return
    }
    // 展开独立的表格容器，直接收集内部的 table，让 splitTable 能正确处理跨页拆分
    if (element.matches('.ir-report-table-wrap')) {
      const table = element.querySelector(':scope > table')
      if (table) {
        units.push({ element: table, keepWithNext: false })
        return
      }
    }
    units.push({
      element,
      keepWithNext: element.matches('.ir-report-chapter-heading, .ir-report-heading'),
    })
  }

  for (const chapter of source.querySelectorAll(':scope > .ir-report-section')) {
    for (const element of chapter.children) append(element)
  }
  source.querySelectorAll(':scope > .ir-disclaimer').forEach(append)
  units.forEach((unit, index) => {
    unit.beforeGap = measuredGap(units[index - 1]?.element, unit.element)
  })
  return units
}

export function paginateReportDom({ source, host, pageHeight, tolerance = DEFAULT_TOLERANCE }) {
  if (!source || !host) throw new Error('缺少报告分页容器')
  host.replaceChildren()
  const pages = []

  const createPage = () => {
    const page = document.createElement('section')
    page.className = 'ir-report-print-page ir-report-print-page--body'
    page.dataset.page = String(pages.length + 2)
    const content = document.createElement('div')
    content.className = 'ir-report-print-page__content'
    page.appendChild(content)
    page.appendChild(createReportWatermark())
    host.appendChild(page)
    const model = { page, content }
    pages.push(model)
    return model
  }

  let current = createPage()
  const units = collectPrintUnits(source)

  for (let index = 0; index < units.length; index += 1) {
    const unit = units[index]
    const clone = applyBeforeGap(unit.element.cloneNode(true), unit.beforeGap)
    const isTable = unit.element.matches('table')
    if (isTable) {
      const lastPage = splitTable(unit.element, current, createPage, pageHeight, tolerance, unit.beforeGap)
      if (!lastPage) throw new Error(`报告表格超过单页且无法安全拆分：${unit.element.className || unit.element.tagName}`)
      current = lastPage
      continue
    }

    current.content.appendChild(clone)

    if (unit.keepWithNext && units[index + 1]) {
      const { probes, hasSplittableTable } = keepWithNextProbes(units, index + 1)
      current.content.append(...probes)
      const groupFits = fits(current.content, pageHeight, tolerance)
      for (const probe of probes) probe.remove()
      // 如果后续包含可拆分表格，即使探测放不下也不换页，让表格自然拆分
      if (!groupFits && !hasSplittableTable && current.content.children.length > 1) {
        clone.remove()
        current = createPage()
        current.content.appendChild(clone)
      }
    }

    if (fits(current.content, pageHeight, tolerance)) continue
    clone.remove()
    if (current.content.children.length) current = createPage()
    current.content.appendChild(clone)
    if (fits(current.content, pageHeight, tolerance)) continue

    clone.remove()
    const isAnalysis = unit.element.classList.contains('ir-report-ai-analysis')
    const split = isAnalysis
      ? splitAnalysis(unit.element, createPage, pageHeight, tolerance)
      : splitTextElement(unit.element, createPage, pageHeight, tolerance)
    if (!split) throw new Error(`报告内容超过单页且无法安全拆分：${unit.element.className || unit.element.tagName}`)
    current = pages.at(-1)
  }

  for (const model of [...pages]) {
    if (!model.content.children.length) {
      model.page.remove()
      pages.splice(pages.indexOf(model), 1)
    }
  }
  pages.forEach((model, index) => {
    model.page.dataset.page = String(index + 2)
    model.page.classList.toggle('ir-report-print-page--last', index === pages.length - 1)
  })

  return { pages: pages.map(({ page }) => page), unitCount: units.length }
}

export async function waitForPrintAssets(root) {
  if (document.fonts?.ready) await document.fonts.ready

  const chartCount = root.querySelectorAll('.ir-report-chart').length
  if (chartCount) {
    const started = performance.now()
    while (root.querySelectorAll('.ir-report-chart__print[src]').length < chartCount) {
      if (performance.now() - started > 5000) throw new Error('报告图表快照尚未准备完成')
      await new Promise((resolve) => requestAnimationFrame(resolve))
    }
  }

  const images = [...root.querySelectorAll('img')]
  await Promise.all(images.map(async (image) => {
    if (image.complete && image.naturalWidth) return
    if (typeof image.decode === 'function') {
      try { await image.decode(); return } catch { /* fall through to load event */ }
    }
    await new Promise((resolve) => {
      image.addEventListener('load', resolve, { once: true })
      image.addEventListener('error', resolve, { once: true })
    })
  }))
}
