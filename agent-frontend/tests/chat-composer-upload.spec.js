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

  it('blocks send while validating and shows ready file coverage', async () => {
    const uploading = mountComposer({ spotUploading: true })
    await uploading.get('textarea').setValue('测算山西 100MW/200MWh')
    expect(uploading.get('.ir-composer__send').attributes('disabled')).toBeDefined()
    expect(uploading.text()).toContain('正在解析并计算 19 个充放电档位')

    const ready = mountComposer({
      spotContext: {
        status: 'ready', fileName: '山西电价.xlsx',
        startDate: '2025-01-01', endDate: '2025-12-31', validDays: 365,
      },
    })
    expect(ready.text()).toContain('山西电价.xlsx')
    expect(ready.text()).toContain('有效 365 天')
    expect(ready.text()).toContain('本会话使用')
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
