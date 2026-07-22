import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'

const chart = vi.hoisted(() => ({
  init: vi.fn(),
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
}))

vi.mock('echarts', () => ({
  init: chart.init,
}))

import { useEcharts } from '@/views/home/composables/useEcharts'

const resizeObservers = []

class ResizeObserverStub {
  constructor(callback) {
    this.callback = callback
    this.observe = vi.fn()
    this.disconnect = vi.fn()
    resizeObservers.push(this)
  }
}

const ChartHost = defineComponent({
  setup() {
    const { el } = useEcharts(() => ({ series: [] }))
    return () => h('div', { ref: el, style: 'width: 100px; height: 100px;' })
  },
})

describe('useEcharts 图表容器尺寸变化', () => {
  beforeEach(() => {
    resizeObservers.length = 0
    chart.init.mockReturnValue({
      setOption: chart.setOption,
      resize: chart.resize,
      dispose: chart.dispose,
    })
    chart.init.mockClear()
    chart.setOption.mockClear()
    chart.resize.mockClear()
    chart.dispose.mockClear()
    global.ResizeObserver = ResizeObserverStub
  })

  afterEach(() => {
    delete global.ResizeObserver
  })

  it('容器尺寸变化时主动 resize，避免加载态恢复后图表仍按隐藏尺寸渲染', async () => {
    const wrapper = mount(ChartHost, { attachTo: document.body })
    await nextTick()

    expect(resizeObservers).toHaveLength(1)
    expect(resizeObservers[0].observe).toHaveBeenCalledWith(wrapper.element)

    resizeObservers[0].callback([{ target: wrapper.element }])

    expect(chart.resize).toHaveBeenCalledTimes(1)
    wrapper.unmount()
    expect(resizeObservers[0].disconnect).toHaveBeenCalledTimes(1)
  })
})
