import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCalculationStore } from '@/store/modules/calculation'

const api = vi.hoisted(() => ({
  createCalculationTask: vi.fn(),
  getCalculationTask: vi.fn(),
  getCalculationResult: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
  renameConversation: vi.fn(),
  getParamDict: vi.fn(),
  getStations: vi.fn(),
}))

vi.mock('@/api/calc', () => api)
vi.mock('@/api/report', () => ({ createReport: vi.fn(), getReportTask: vi.fn() }))
vi.mock('@/utils/reportSse', () => ({ streamReportEvents: vi.fn() }))
vi.mock('@/utils/chatSse', () => ({ openChatStream: vi.fn() }))

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('calculation station remote query', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('keeps the selected node and appends cursor pages without duplicates', async () => {
    api.getStations
      .mockResolvedValueOnce({ data: { items: ['节点01', '节点02'], hasMore: true, nextCursor: '节点02' } })
      .mockResolvedValueOnce({ data: { items: ['节点02', '节点03'], hasMore: false, nextCursor: null } })
    const store = useCalculationStore()

    await store.searchStations({ province: '甘肃', selectedNode: '历史节点' })
    await store.loadMoreStations({ selectedNode: '历史节点' })

    expect(api.getStations).toHaveBeenNthCalledWith(1, expect.objectContaining({
      province: '甘肃', keyword: '', limit: 30,
    }))
    expect(api.getStations).toHaveBeenNthCalledWith(2, expect.objectContaining({
      province: '甘肃', keyword: '', cursor: '节点02', limit: 30,
    }))
    expect(store.stationOptions).toEqual(['历史节点', '节点01', '节点02', '节点03'])
    expect(store.stationHasMore).toBe(false)
  })

  it('uses the last keyword response and silently ignores an aborted request', async () => {
    const first = deferred()
    const second = deferred()
    api.getStations.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const store = useCalculationStore()

    const oldSearch = store.searchStations({ province: '甘肃', keyword: '旧' })
    const oldSignal = api.getStations.mock.calls[0][0].signal
    const newSearch = store.searchStations({ province: '甘肃', keyword: '新' })
    expect(oldSignal.aborted).toBe(true)

    second.resolve({ data: { items: ['新节点'], hasMore: false, nextCursor: null } })
    await newSearch
    first.resolve({ data: { items: ['旧节点'], hasMore: false, nextCursor: null } })
    await oldSearch

    expect(store.stationKeyword).toBe('新')
    expect(store.stationOptions).toEqual(['新节点'])
    expect(store.stationError).toBe('')
  })

  it('keeps existing options when the same query is requested again', async () => {
    const pending = deferred()
    api.getStations.mockReturnValueOnce(pending.promise)
    const store = useCalculationStore()
    store.stationProvince = '甘肃'
    store.stationKeyword = ''
    store.stationOptions = ['节点01']

    const search = store.searchStations({ province: '甘肃' })

    expect(store.stationOptions).toEqual(['节点01'])
    pending.resolve({ data: { items: ['节点02', '节点03'], hasMore: false, nextCursor: null } })
    await search
    expect(store.stationOptions).toEqual(['节点01', '节点02', '节点03'])
  })

  it('deduplicates an in-flight query and serves a subsequent query from cache', async () => {
    const pending = deferred()
    api.getStations.mockReturnValueOnce(pending.promise)
    const store = useCalculationStore()

    const first = store.searchStations({ province: '甘肃', keyword: '兰州' })
    const duplicate = store.searchStations({ province: '甘肃', keyword: '兰州' })
    expect(api.getStations).toHaveBeenCalledTimes(1)

    pending.resolve({ data: { items: ['兰州东'], hasMore: false, nextCursor: null } })
    await Promise.all([first, duplicate])
    await store.searchStations({ province: '甘肃', keyword: '兰州' })

    expect(api.getStations).toHaveBeenCalledTimes(1)
    expect(store.stationOptions).toEqual(['兰州东'])
  })

  it('reset invalidates the current request and clears remote-query state', async () => {
    const pending = deferred()
    api.getStations.mockReturnValueOnce(pending.promise)
    const store = useCalculationStore()

    const search = store.searchStations({ province: '甘肃' })
    const signal = api.getStations.mock.calls[0][0].signal
    store.resetStationQuery()
    pending.resolve({ data: { items: ['不应采用'], hasMore: true, nextCursor: '不应采用' } })
    await search

    expect(signal.aborted).toBe(true)
    expect(store.stationProvince).toBe('')
    expect(store.stationOptions).toEqual([])
    expect(store.stationLoading).toBe(false)
  })

  it('keeps options empty when the province has no station rows', async () => {
    api.getStations.mockResolvedValueOnce({ data: { items: [], hasMore: false, nextCursor: null } })
    const store = useCalculationStore()

    await store.searchStations({ province: '无节点省' })

    expect(store.stationProvince).toBe('无节点省')
    expect(store.stationOptions).toEqual([])
    expect(store.stationHasMore).toBe(false)
    expect(store.stationError).toBe('')
  })

  it('switching province replaces previous options without stale residue', async () => {
    api.getStations
      .mockResolvedValueOnce({ data: { items: ['节点01'], hasMore: false, nextCursor: null } })
      .mockResolvedValueOnce({ data: { items: ['郑州'], hasMore: false, nextCursor: null } })
    const store = useCalculationStore()

    await store.searchStations({ province: '甘肃' })
    expect(store.stationOptions).toEqual(['节点01'])

    await store.searchStations({ province: '河南' })
    expect(store.stationProvince).toBe('河南')
    expect(store.stationOptions).toEqual(['郑州'])
  })
})
