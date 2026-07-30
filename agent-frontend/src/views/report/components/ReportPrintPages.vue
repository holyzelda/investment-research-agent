<template>
  <div ref="host" class="ir-report-print-pages" aria-hidden="true" />
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { paginateReportDom, waitForPrintAssets } from '../utils/paginateReport'

const host = ref(null)
let preparing = null
let generation = 0

function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

async function prepareForPrint(source) {
  if (preparing) return preparing
  const token = ++generation
  preparing = (async () => {
    await nextTick()
    await waitForPrintAssets(source)
    await nextFrame()

    const probe = document.createElement('section')
    probe.className = 'ir-report-print-page ir-report-print-page--body ir-report-print-page--probe'
    const content = document.createElement('div')
    content.className = 'ir-report-print-page__content'
    probe.appendChild(content)
    host.value.replaceChildren(probe)
    await nextFrame()
    const pageHeight = content.clientHeight
    probe.remove()
    if (!pageHeight) throw new Error('无法测量报告打印页面')
    if (token !== generation) return null

    const result = paginateReportDom({ source, host: host.value, pageHeight })
    await nextTick()
    await nextFrame()
    return result
  })().finally(() => { preparing = null })
  return preparing
}

function clear() {
  generation += 1
  host.value?.replaceChildren()
}

defineExpose({ prepareForPrint, clear })
</script>
