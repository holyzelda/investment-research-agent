import { chromium } from 'playwright'

const url = 'http://127.0.0.1:5212/tie-line'
const executablePath = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const viewports = [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
]

const browser = await chromium.launch({ executablePath, headless: true })
for (const viewport of viewports) {
  const page = await browser.newPage({ viewport })
  await page.goto(url, { waitUntil: 'networkidle' })
  await page.screenshot({ path: `tie-line-filter-${viewport.width}x${viewport.height}.png`, fullPage: true })
  const result = await page.evaluate(() => {
    const bar = document.querySelector('.tl-filterbar')
    const controls = [...document.querySelectorAll('.tl-filter-control')]
    const reset = document.querySelector('.tl-filterbar__reset')
    const bodyWidth = document.documentElement.clientWidth
    const scrollWidth = document.documentElement.scrollWidth
    return {
      hasBar: Boolean(bar),
      barText: bar?.textContent?.replace(/\s+/g, ' ').trim() || '',
      controlCount: controls.length,
      resetDisabled: reset?.hasAttribute('disabled') ?? null,
      hasHorizontalOverflow: scrollWidth > bodyWidth,
    }
  })
  console.log(`${viewport.width}x${viewport.height}`, JSON.stringify(result))
  await page.close()
}
await browser.close()
