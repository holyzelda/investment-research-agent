import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTieLineStore } from '@/store/modules/tieLine'

const lines = [
  { id: 1, startRegion: '西北', endRegion: '华南' },
  { id: 2, startRegion: '西北', endRegion: '华东' },
  { id: 3, startRegion: '华北', endRegion: '华南' },
]

function visibleIds(store) {
  return store.visibleLines.map((line) => line.id)
}

describe('联络线地图区域筛选', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('未选择区域时展示全部线路', () => {
    const store = useTieLineStore()
    store.lines = lines

    expect(visibleIds(store)).toEqual([1, 2, 3])
  })

  it('分别按起点或终点区域精确筛选', () => {
    const store = useTieLineStore()
    store.lines = lines

    store.setStartRegion('西北')
    expect(visibleIds(store)).toEqual([1, 2])

    store.setStartRegion('')
    store.setEndRegion('华南')
    expect(visibleIds(store)).toEqual([1, 3])
  })

  it('同时选择起点和终点时要求两端均精确匹配', () => {
    const store = useTieLineStore()
    store.lines = lines

    store.setStartRegion('西北')
    store.setEndRegion('华南')

    expect(visibleIds(store)).toEqual([1])
  })

  it('筛选隐藏已选线路时清空详情，仍可见时保留选择', () => {
    const store = useTieLineStore()
    store.lines = lines
    store.selectedId = 1
    store.detail = { id: 1 }

    store.setStartRegion('西北')
    expect(store.selectedId).toBe(1)
    expect(store.detail).toEqual({ id: 1 })

    store.setEndRegion('华东')
    expect(store.selectedId).toBeNull()
    expect(store.detail).toBeNull()
  })
})
