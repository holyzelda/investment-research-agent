export const REPORT_WATERMARK_TEXT = '西安奇点能源股份有限公司'
export const REPORT_WATERMARK_COLUMNS = 3
export const REPORT_WATERMARK_ROWS = 5

export function createReportWatermark({
  text = REPORT_WATERMARK_TEXT,
  columns = REPORT_WATERMARK_COLUMNS,
  rows = REPORT_WATERMARK_ROWS,
} = {}) {
  const watermark = document.createElement('div')
  watermark.className = 'ir-report-watermark'
  watermark.setAttribute('aria-hidden', 'true')
  watermark.style.setProperty('--ir-report-watermark-columns', String(columns))
  watermark.style.setProperty('--ir-report-watermark-rows', String(rows))

  for (let index = 0; index < columns * rows; index += 1) {
    const cell = document.createElement('span')
    cell.className = 'ir-report-watermark__cell'
    const label = document.createElement('span')
    label.className = 'ir-report-watermark__text'
    label.textContent = text
    cell.appendChild(label)
    watermark.appendChild(cell)
  }

  return watermark
}
