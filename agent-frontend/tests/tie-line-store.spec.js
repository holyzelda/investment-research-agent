import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTieLineStore, parseLengthKm } from '@/store/modules/tieLine'

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

  it('按当前可见范围推荐长度最长的线路', () => {
    const store = useTieLineStore()
    store.lines = [
      { id: 3, startRegion: '西北', endRegion: '华南', lengthText: '1,525.2 km' },
      { id: 2, startRegion: '西北', endRegion: '华东', lengthText: '2383km' },
      { id: 1, startRegion: '华北', endRegion: '华南', lengthText: '2383 km' },
      { id: 4, startRegion: '西北', endRegion: '华南', lengthText: null },
    ]

    expect(store.recommendedLine.id).toBe(1)

    store.setStartRegion('西北')
    expect(store.recommendedLine.id).toBe(2)

    store.setEndRegion('华南')
    expect(store.recommendedLine.id).toBe(3)
  })

  it('跳过无法解析长度的线路，并在没有有效候选时不推荐', () => {
    expect(parseLengthKm('1,525.2 km')).toBe(1525.2)
    expect(parseLengthKm('716 km')).toBe(716)
    expect(parseLengthKm('2383km')).toBe(2383)
    expect(parseLengthKm(null)).toBeNull()
    expect(parseLengthKm('长度未知')).toBeNull()

    const store = useTieLineStore()
    store.lines = [{ id: 1, startRegion: '西北', endRegion: '华南', lengthText: '长度未知' }]
    expect(store.recommendedLine).toBeNull()
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
