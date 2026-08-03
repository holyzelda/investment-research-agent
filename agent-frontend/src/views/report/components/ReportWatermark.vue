<template>
  <div
    ref="watermark"
    class="ir-report-watermark"
    aria-hidden="true"
    :style="{
      '--ir-report-watermark-columns': REPORT_WATERMARK_COLUMNS,
      '--ir-report-watermark-rows': rows,
    }"
  >
    <span
      v-for="index in REPORT_WATERMARK_COLUMNS * rows"
      :key="index"
      class="ir-report-watermark__cell"
    >
      <span class="ir-report-watermark__text">{{ REPORT_WATERMARK_TEXT }}</span>
    </span>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  REPORT_WATERMARK_COLUMNS,
  REPORT_WATERMARK_ROWS,
  REPORT_WATERMARK_TEXT,
} from '../utils/reportWatermark'

const watermark = ref(null)
const rows = ref(REPORT_WATERMARK_ROWS)
let resizeObserver = null

function updateRows() {
  const container = watermark.value?.parentElement
  if (!container) return
  const { width, height } = container.getBoundingClientRect()
  if (!width || !height) return
  const a4Height = width * 297 / 210
  rows.value = Math.max(REPORT_WATERMARK_ROWS, Math.ceil(height / a4Height * REPORT_WATERMARK_ROWS))
}

onMounted(() => {
  updateRows()
  if (typeof ResizeObserver !== 'undefined' && watermark.value?.parentElement) {
    resizeObserver = new ResizeObserver(updateRows)
    resizeObserver.observe(watermark.value.parentElement)
  }
})

onBeforeUnmount(() => resizeObserver?.disconnect())
</script>
