import { defineStore } from 'pinia'
import { getTieLines, getTieLineDetail } from '@/api/tieLine'

// 联络线地图状态：线路列表、静态统计、筛选（电压/区域）与选中详情。
// 首版只做地图展示，不含任何功率时序（底表无时序字段）。
export const useTieLineStore = defineStore('tieLine', {
  state: () => ({
    lines: [],
    stats: null,
    filters: { voltageOptions: [], regionOptions: [] },
    activeVoltage: '',
    activeRegion: '',
    selectedId: null,
    detail: null,
    loading: false,
    error: '',
  }),
  getters: {
    // 按电压/区域筛选后的可见线路（地图与列表共用同一份）
    visibleLines(state) {
      return state.lines.filter((line) => {
        if (state.activeVoltage && line.voltageText !== state.activeVoltage) return false
        if (
          state.activeRegion &&
          line.startRegion !== state.activeRegion &&
          line.endRegion !== state.activeRegion
        ) {
          return false
        }
        return true
      })
    },
    selectedLine(state) {
      return state.lines.find((line) => line.id === state.selectedId) || null
    },
  },
  actions: {
    async loadLines() {
      this.loading = true
      this.error = ''
      try {
        const res = await getTieLines()
        const data = res?.data || {}
        this.lines = data.items || []
        this.stats = data.stats || null
        this.filters = data.filters || { voltageOptions: [], regionOptions: [] }
      } catch (e) {
        this.error = '联络线数据加载失败，请稍后重试'
        this.lines = []
      } finally {
        this.loading = false
      }
    },
    async selectLine(id) {
      this.selectedId = id
      // 详情静态字段列表接口已包含；这里再取一次以拿溯源字段（coordinateBasis 等）
      try {
        const res = await getTieLineDetail(id)
        this.detail = res?.data || null
      } catch (e) {
        this.detail = this.selectedLine // 详情接口失败时退回列表里的基础字段
      }
    },
    setVoltage(value) {
      this.activeVoltage = value || ''
      this._dropSelectionIfHidden()
    },
    setRegion(value) {
      this.activeRegion = value || ''
      this._dropSelectionIfHidden()
    },
    clearSelection() {
      this.selectedId = null
      this.detail = null
    },
    // 选中的线路被筛掉后，清空右侧详情，避免展示与地图不一致
    _dropSelectionIfHidden() {
      if (
        this.selectedId != null &&
        !this.visibleLines.some((line) => line.id === this.selectedId)
      ) {
        this.clearSelection()
      }
    },
  },
})
