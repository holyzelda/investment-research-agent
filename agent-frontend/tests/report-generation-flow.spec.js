import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const reportApi = vi.hoisted(() => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
const calcApi = vi.hoisted(() => ({ getConversation: vi.fn(), listConversations: vi.fn() }))
const stream = vi.hoisted(() => vi.fn())
vi.mock('@/api/calc', () => calcApi)
vi.mock('@/api/report', () => reportApi)
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: stream }))

import { useCalculationStore } from '@/store/modules/calculation'
import { thinkingNodes } from '@/utils/thinkingChain'

describe('report generation conversation cards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders report steps through the shared thinking chain and answer message', async () => {
    reportApi.createReport.mockResolvedValue({
      data: {
        reportTaskId: 8,
        taskId: 42,
        status: 'generating',
        steps: [{ seq: 1, key: 'prepare', title: '读取冻结测算快照', state: 'active' }],
      },
    })
    stream.mockImplementation(async (_id, { onEvent }) => {
      onEvent({ type: 'step', data: { seq: 2, key: 'prepare', title: '读取冻结测算快照', state: 'completed' } })
      onEvent({ type: 'step', data: { seq: 3, key: 'ai', title: '生成智能分析', state: 'active' } })
      onEvent({
        type: 'complete',
        data: {
          reportTaskId: 8,
          taskId: 42,
          reportId: 'r-8',
          status: 'completed',
          steps: [{ seq: 4, key: 'ai', title: '生成智能分析', state: 'completed' }],
        },
      })
    })
    const store = useCalculationStore()
    store.versions = [{ taskId: 42, version: 'V1' }]

    await store.generateReport(42)

    const message = store.messages.find((item) => item.flow === 'report')
    const nodes = thinkingNodes(message.thinkingState)
    expect(message.kind).toBe('assistant-stream')
    expect(nodes.map((node) => node.title)).toEqual(['读取冻结测算快照', '生成智能分析'])
    expect(nodes.every((node) => node.status === 'completed')).toBe(true)
    expect(message).toMatchObject({
      phase: 'completed',
      reportId: 'r-8',
      answerText: '正式报告已生成，可查看完整报告。',
      done: true,
    })
    expect(message.payload.report_id).toBe('r-8')
  })

  it('renders failed generation as an aborted thinking chain and shared error answer', async () => {
    reportApi.createReport.mockResolvedValue({
      data: { reportTaskId: 8, taskId: 42, status: 'generating', steps: [] },
    })
    stream.mockImplementation(async (_id, { onEvent }) => {
      onEvent({ type: 'step', data: { seq: 1, key: 'ai', title: '生成智能分析', state: 'active' } })
      onEvent({
        type: 'failed',
        data: {
          reportTaskId: 8,
          taskId: 42,
          status: 'failed',
          error: { message: '中台调用失败' },
          steps: [{ seq: 2, key: 'ai', title: '生成智能分析', state: 'failed' }],
        },
      })
    })
    const store = useCalculationStore()
    store.versions = [{ taskId: 42, version: 'V1' }]

    await store.generateReport(42)

    const message = store.messages.find((item) => item.flow === 'report')
    expect(thinkingNodes(message.thinkingState).some((node) => node.status === 'aborted')).toBe(true)
    expect(message.phase).toBe('error')
    expect(message.answerText).toContain('中台调用失败')
    expect(message.reportId).toBeNull()
  })

  it('syncs completed report metadata from the conversation without replacing messages', async () => {
    reportApi.createReport.mockResolvedValue({ data: { reportTaskId: 8, taskId: 42, status: 'generating', steps: [] } })
    calcApi.getConversation.mockResolvedValue({
      data: {
        reports: [{ reportId: 'r-8', taskId: 42, version: 'V1', title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56', status: 'completed' }],
        versions: [{ taskId: 42, report: { reportId: 'r-8', title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56', status: 'completed' } }],
      },
    })
    stream.mockImplementation(async (_id, { onEvent }) => {
      onEvent({ type: 'complete', data: { reportTaskId: 8, taskId: 42, reportId: 'r-8', status: 'completed' } })
    })
    const store = useCalculationStore()
    store.conversationId = 'c-1'
    store.selectedVersion = 'V1'
    store.versions = [{ taskId: 42, version: 'V1' }]
    store.messages = [{ id: 'm-existing', kind: 'text', text: '保留消息' }]

    await store.generateReport(42)
    await Promise.resolve()

    expect(calcApi.getConversation).toHaveBeenCalledWith('c-1')
    expect(store.reports).toHaveLength(1)
    expect(store.reports[0]).toMatchObject({ title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56' })
    expect(store.versions[0].report).toMatchObject({ title: '甘肃项目投资报告' })
    expect(store.selectedVersion).toBe('V1')
    expect(store.messages.find((message) => message.id === 'm-existing')).toBeTruthy()
  })
})
