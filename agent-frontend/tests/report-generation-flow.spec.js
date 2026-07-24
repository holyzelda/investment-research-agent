import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const reportApi = vi.hoisted(() => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
const stream = vi.hoisted(() => vi.fn())
vi.mock('@/api/calc', () => ({ listConversations: vi.fn() }))
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
})
