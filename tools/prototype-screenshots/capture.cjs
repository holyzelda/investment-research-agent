const { existsSync } = require('node:fs')
const { mkdir } = require('node:fs/promises')
const { pathToFileURL } = require('node:url')
const path = require('node:path')
const { chromium } = require('playwright')

const repoRoot = process.env.REPO_ROOT || '/workspace'
const prototypePath = path.join(
  repoRoot,
  'docs/superpowers/prototypes/graphical-selection-captcha.html',
)
const outputDirectory = path.join(
  repoRoot,
  'docs/superpowers/prototypes/screenshots',
)

if (!existsSync(prototypePath)) {
  throw new Error(`Prototype not found: ${prototypePath}`)
}

async function openPrototype(browser, viewport) {
  const page = await browser.newPage({
    viewport,
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
  })
  await page.goto(pathToFileURL(prototypePath).href)
  await page.locator('.tile').first().waitFor()
  return page
}

async function capture() {
  await mkdir(outputDirectory, { recursive: true })
  const browser = await chromium.launch({ args: ['--no-sandbox'] })

  try {
    const desktop = await openPrototype(browser, { width: 1440, height: 1000 })
    await desktop.locator('.tile').nth(0).click()
    await desktop.locator('.tile').nth(2).click()
    await desktop.screenshot({
      path: path.join(outputDirectory, 'desktop-selected.png'),
      fullPage: true,
    })
    await desktop.close()

    const mobile = await openPrototype(browser, { width: 360, height: 800 })
    await mobile.locator('.tile').first().click()
    await mobile.getByRole('button', { name: '验证', exact: true }).click()
    await mobile.locator('#captcha.is-verified').waitFor()
    await mobile.screenshot({
      path: path.join(outputDirectory, 'mobile-verified.png'),
      fullPage: true,
    })
    await mobile.close()
  } finally {
    await browser.close()
  }

  console.log(`Screenshots written to ${outputDirectory}`)
}

capture().catch(error => {
  console.error(error)
  process.exitCode = 1
})
