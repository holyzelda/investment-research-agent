import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

// 轻量 ECharts 生命周期封装：挂载即初始化、option 变化即 setOption、容器尺寸变化自适应、卸载销毁。
// 传入一个返回 option 的工厂，随响应式依赖变化自动重绘。
export function useEcharts(optionFactory) {
  const el = ref(null)
  let chart = null
  let resizeObserver = null

  const render = () => {
    if (!chart) return
    chart.setOption(optionFactory(), true)
  }
  const resize = () => chart && chart.resize()

  onMounted(() => {
    chart = echarts.init(el.value)
    render()
    window.addEventListener('resize', resize)
    if (typeof ResizeObserver !== 'undefined' && el.value) {
      resizeObserver = new ResizeObserver(resize)
      resizeObserver.observe(el.value)
    }
  })
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    resizeObserver && resizeObserver.disconnect()
    resizeObserver = null
    chart && chart.dispose()
    chart = null
  })

  // option 依赖变化时重绘
  watch(optionFactory, render, { deep: true })

  return { el, resize }
}

// 读取 XC 图表色板（--xc-chart-1..8），供 ECharts 使用。
export function xcChartColors() {
  const s = getComputedStyle(document.documentElement)
  return Array.from({ length: 8 }, (_, i) => s.getPropertyValue(`--xc-chart-${i + 1}`).trim()).filter(Boolean)
}

export function xcVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
