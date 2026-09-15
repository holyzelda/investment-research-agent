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
  it('exposes the upload format help and purpose selector', () => {
    const wrapper = mountComposer()

    expect(wrapper.get('.ir-composer__hint-trigger').attributes('aria-label')).toBe('查看电价文件格式要求')
    expect(wrapper.get('.ir-composer__price-mode').text()).toContain('充放电通用')
  })

  it('emits the selected xlsx file for immediate validation', async () => {
    const wrapper = mountComposer()
    const file = new File(['xlsx'], 'spot.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })

    await input.trigger('change')

    expect(wrapper.emitted('spot-upload')?.[0]?.[0]).toEqual({ file, priceMode: 'both' })
  })

  it('blocks send while processing and shows the upload stages', async () => {
    const uploading = mountComposer({
      spotUploading: true,
      spotProgress: {
        phase: 'validating', fileName: '山西现货电价.xlsx',
        message: '正在读取并校验 Excel 数据',
      },
    })
    await uploading.get('textarea').setValue('测算山西 100MW/200MWh')
    expect(uploading.get('.ir-composer__send').attributes('disabled')).toBeDefined()
    expect(uploading.text()).toContain('山西现货电价.xlsx')
    expect(uploading.text()).toContain('文件上传')
    expect(uploading.text()).toContain('格式校验')
    expect(uploading.text()).not.toContain('数据计算')
    expect(uploading.findAll('.ir-composer__step.is-complete')).toHaveLength(1)
    expect(uploading.get('.ir-composer__step.is-active').text()).toContain('格式校验')
  })

  it('emits the selected price purpose and locks a ready file', async () => {
    const wrapper = mountComposer()
    await wrapper.get('.ir-composer__price-mode button:nth-child(2)').trigger('click')
    const file = new File(['xlsx'], 'charge.xlsx')
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    expect(wrapper.emitted('spot-upload')?.[0]?.[0]).toEqual({ file, priceMode: 'charge_only' })

    const ready = mountComposer({ spotContext: { status: 'ready', fileName: 'charge.xlsx', priceMode: 'charge_only' } })
    expect(ready.find('.ir-composer__attachment-remove').exists()).toBe(false)
    expect(ready.get('.ir-composer__price-mode button:nth-child(1)').attributes('disabled')).toBeDefined()
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

  it('allows closing an upload error without unlocking a ready context', async () => {
    const wrapper = mountComposer({
      spotError: '表头不匹配',
    })
    await wrapper.get('.ir-composer__attachment-remove').trigger('click')
    expect(wrapper.emitted('spot-error-dismiss')).toHaveLength(1)
  })
})
