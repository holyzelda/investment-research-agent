import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const reportApi = vi.hoisted(() => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
const calcApi = vi.hoisted(() => ({ getConversation: vi.fn(), listConversations: vi.fn() }))
const stream = vi.hoisted(() => vi.fn())
vi.mock('@/api/calc', () => calcApi)
vi.mock('@/api/report', () => reportApi)
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: stream }))

import { useCalculationStore } from '@/store/modules/calculation'

describe('report generation conversation cards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('adds a progress card and replaces it with a report card after SSE completion', async () => {
    reportApi.createReport.mockResolvedValue({ data: { reportTaskId: 8, taskId: 42, status: 'generating', steps: [] } })
    stream.mockImplementation(async (_id, { onEvent }) => {
      onEvent({ type: 'step', data: { key: 'prepare', title: '读取冻结测算快照', state: 'active' } })
      onEvent({ type: 'complete', data: { reportTaskId: 8, taskId: 42, reportId: 'r-8', status: 'completed' } })
    })
    const store = useCalculationStore()
    store.versions = [{ taskId: 42, version: 'V1' }]

    await store.generateReport(42)

    const card = store.messages.find((message) => message.kind === 'report-generated')
    expect(card.steps[0].title).toBe('读取冻结测算快照')
    expect(card.payload.report_id).toBe('r-8')
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

    expect(calcApi.getConversation).toHaveBeenCalledWith('c-1')
    expect(store.reports).toHaveLength(1)
    expect(store.reports[0]).toMatchObject({ title: '甘肃项目投资报告', createdAt: '2026-07-27T14:10:56' })
    expect(store.versions[0].report).toMatchObject({ title: '甘肃项目投资报告' })
    expect(store.selectedVersion).toBe('V1')
    expect(store.messages.find((message) => message.id === 'm-existing')).toBeTruthy()
  })
})
