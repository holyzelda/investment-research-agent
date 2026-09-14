import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ChatComposer from '@/views/home/components/ChatComposer.vue'

const ElInputStub = {
  props: ['modelValue', 'disabled'],
  emits: ['update:modelValue'],
  template: '<textarea :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  methods: { focus() {} },
}

function mountComposer(props = {}) {
  return mount(ChatComposer, {
    props,
    global: { stubs: { ElInput: ElInputStub } },
  })
}

describe('ChatComposer spot price attachment', () => {
  it('explains the upload purpose, required headers, time range, and price unit', () => {
    const wrapper = mountComposer()

    expect(wrapper.get('.ir-composer__hint').text()).toBe(
      '上传现货电价 Excel 文件，用于按文件中的电价数据测算储能收益。表头必须为：日期、时点（00:15 至 24:00）、电价（元/MWh）',
    )
  })

  it('emits the selected xlsx file for immediate validation', async () => {
    const wrapper = mountComposer()
    const file = new File(['xlsx'], 'spot.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')

    expect(wrapper.emitted('spot-upload')?.[0]?.[0]).toBe(file)
  })

  it('blocks send while processing and shows the real progress stages', async () => {
    const uploading = mountComposer({
      spotUploading: true,
      spotProgress: {
        phase: 'computing', fileName: '山西现货电价.xlsx',
        completedDays: 186, totalDays: 365,
        message: '正在计算不同充放电策略',
      },
    })
    await uploading.get('textarea').setValue('测算山西 100MW/200MWh')
    expect(uploading.get('.ir-composer__send').attributes('disabled')).toBeDefined()
    expect(uploading.text()).toContain('山西现货电价.xlsx')
    expect(uploading.text()).toContain('文件上传')
    expect(uploading.text()).toContain('格式校验')
    expect(uploading.text()).toContain('数据计算')
    expect(uploading.text()).toContain('已完成 186/365 个有效日')
    expect(uploading.findAll('.ir-composer__step.is-complete')).toHaveLength(2)
    expect(uploading.get('.ir-composer__step.is-active').text()).toContain('数据计算')
  })

  it('shows skipped days as a non-blocking warning in the ready summary', async () => {
    const ready = mountComposer({
      spotContext: {
        status: 'ready', fileName: '山西电价.xlsx',
        startDate: '2025-01-01', endDate: '2025-12-31', validDays: 362, skippedDays: 3,
      },
    })

    expect(ready.text()).toContain('山西电价.xlsx')
    expect(ready.text()).toContain('有效 362 天')
    expect(ready.get('.is-warning').text()).toContain('跳过 3 天')
    expect(ready.text()).toContain('本会话使用')
    await ready.get('textarea').setValue('继续测算')
    expect(ready.find('.ir-composer__send').attributes('disabled')).toBeUndefined()
  })

  it('blocks an expired context until the user removes or replaces it', async () => {
    const wrapper = mountComposer({
      spotContext: { status: 'expired', fileName: '旧电价.xlsx' },
    })
    await wrapper.get('textarea').setValue('重新测算')

    expect(wrapper.text()).toContain('自定义电价已失效')
    expect(wrapper.get('.ir-composer__send').attributes('disabled')).toBeDefined()
    await wrapper.get('.ir-composer__attachment-remove').trigger('click')
    expect(wrapper.emitted('spot-remove')).toHaveLength(1)
  })
})
