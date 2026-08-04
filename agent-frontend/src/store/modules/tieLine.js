import { defineStore } from 'pinia'
import { getTieLines, getTieLineDetail, getTieLinePower } from '@/api/tieLine'

export function parseLengthKm(lengthText) {
  if (typeof lengthText !== 'string') return null
  const match = lengthText.replace(/,/g, '').match(/(\d+(?:\.\d+)?)\s*km\b/i)
  if (!match) return null
  const value = Number(match[1])
  return Number.isFinite(value) ? value : null
}

export function normalizeCapacityMw(value) {
  if (value === '' || value === null || value === undefined) return null
  const number = Number(value)
  return Number.isSafeInteger(number) && number >= 0 ? number : null
}

function formatLocalDate(value) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function yesterdayDate(now = new Date()) {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
}

export function getRollingDateRange(days, now = new Date()) {
  const end = yesterdayDate(now)
  const start = new Date(end.getFullYear(), end.getMonth(), end.getDate() - (days - 1))
  return { startDate: formatLocalDate(start), endDate: formatLocalDate(end) }
}

export function getDefaultPowerRange() {
  return { key: 'thirtyDays', ...getRollingDateRange(30) }
}

export function isValidCustomPowerRange(startDate, endDate, now = new Date()) {
  if (!startDate || !endDate || startDate > endDate) return false
  return endDate <= formatLocalDate(yesterdayDate(now))
}

// 联络线地图状态：线路列表、静态统计、起终点区域筛选与选中详情。
// 首版只做地图展示，不含任何功率时序（底表无时序字段）。
export const useTieLineStore = defineStore('tieLine', {
  state: () => ({
    lines: [],
    stats: null,
    filters: { voltageOptions: [], regionOptions: [] },
    activeStartRegion: '',
    activeEndRegion: '',
    activeMinCapacityMw: null,
    activeMaxCapacityMw: null,
    selectedId: null,
    detail: null,
    powerTrend: null,
    powerTrendLoading: false,
    powerTrendError: '',
    powerRange: getDefaultPowerRange(),
    powerRequestVersion: 0,
    loading: false,
    refreshing: false,
    loaded: false,
    lastLoadedAt: null,
    lineRequestVersion: 0,
    error: '',
  }),
  getters: {
    // 按起点/终点区域筛选后的可见线路（地图与列表共用同一份）。
    visibleLines(state) {
      return state.lines.filter((line) => {
        if (state.activeStartRegion && line.startRegion !== state.activeStartRegion) return false
        if (state.activeEndRegion && line.endRegion !== state.activeEndRegion) return false
        if (state.activeMinCapacityMw !== null || state.activeMaxCapacityMw !== null) {
          if (!Number.isSafeInteger(line.ratedCapacityMw) || line.ratedCapacityMw < 0) return false
          if (state.activeMinCapacityMw !== null && line.ratedCapacityMw < state.activeMinCapacityMw) return false
          if (state.activeMaxCapacityMw !== null && line.ratedCapacityMw > state.activeMaxCapacityMw) return false
        }
        return true
      })
    },
    selectedLine(state) {
      return state.lines.find((line) => line.id === state.selectedId) || null
    },
    // 当前地图可见范围内长度最长的线路；无法解析 km 的记录不参与推荐。
    recommendedLine() {
      return this.visibleLines.reduce((recommended, line) => {
        const length = parseLengthKm(line.lengthText)
        if (length === null) return recommended
        if (!recommended) return { line, length }
        if (length > recommended.length) return { line, length }
        if (length === recommended.length && String(line.id).localeCompare(String(recommended.line.id), 'zh-CN', { numeric: true }) < 0) {
          return { line, length }
        }
        return recommended
      }, null)?.line || null
    },
  },
  actions: {
    _invalidatePowerRequests() {
      this.powerRequestVersion += 1
    },
    _clearPowerTrend() {
      this.powerTrend = null
      this.powerTrendLoading = false
      this.powerTrendError = ''
    },
    async loadPowerTrend(range = this.powerRange) {
      const lineId = this.selectedId ?? this.recommendedLine?.id
      if (lineId == null) return
      await this._loadPowerTrendForLine(lineId, range, () => this.selectedId ?? this.recommendedLine?.id)
    },
    async loadRecommendedPowerTrend(range = getDefaultPowerRange()) {
      if (this.selectedId != null) return
      const lineId = this.recommendedLine?.id
      if (lineId == null) {
        this._clearPowerTrend()
        return
      }
      await this._loadPowerTrendForLine(lineId, range, () => this.selectedId == null ? this.recommendedLine?.id : null)
    },
    async _loadPowerTrendForLine(lineId, range, currentLineId) {
      const requestVersion = this.powerRequestVersion + 1
      this.powerRequestVersion = requestVersion
      this.powerRange = range
      this.powerTrend = null
      this.powerTrendLoading = true
      this.powerTrendError = ''
      try {
        const res = await getTieLinePower(lineId, range)
        if (requestVersion === this.powerRequestVersion && currentLineId() === lineId) {
          this.powerTrend = res?.data || null
        }
      } catch (e) {
        if (requestVersion === this.powerRequestVersion && currentLineId() === lineId) {
          this.powerTrendError = '功率趋势加载失败，请稍后重试'
        }
      } finally {
        if (requestVersion === this.powerRequestVersion && currentLineId() === lineId) {
          this.powerTrendLoading = false
        }
      }
    },
    async setPowerRange(key, range) {
      if (!range || !isValidCustomPowerRange(range.startDate, range.endDate)) return false
      await this.loadPowerTrend({ key, ...range })
      return true
    },
    async loadLines({ force = false, silent = false } = {}) {
      if (this.loaded && !force && !silent) return

      const requestVersion = this.lineRequestVersion + 1
      this.lineRequestVersion = requestVersion
      const blocking = !silent

      if (blocking) {
        this.loading = true
        this.refreshing = false
        this.error = ''
      } else {
        this.loading = false
        this.refreshing = true
      }

      try {
        const res = await getTieLines()
        if (requestVersion !== this.lineRequestVersion) return

        const data = res?.data || {}
        this.lines = data.items || []
        this.stats = data.stats || null
        this.filters = data.filters || { voltageOptions: [], regionOptions: [] }
        this.loaded = true
        this.lastLoadedAt = Date.now()
        this.error = ''
        this._dropSelectionIfHidden()
      } catch (e) {
        if (requestVersion !== this.lineRequestVersion) return

        if (!this.loaded) {
          this.error = '联络线数据加载失败，请稍后重试'
          this.lines = []
          this.stats = null
          this.filters = { voltageOptions: [], regionOptions: [] }
        }
      } finally {
        if (requestVersion === this.lineRequestVersion) {
          if (blocking) this.loading = false
          else this.refreshing = false
        }
      }
    },
    async selectLine(id) {
      this._invalidatePowerRequests()
      this.selectedId = id
      this.detail = null
      this._clearPowerTrend()
      const defaultRange = getDefaultPowerRange()
      const trendRequest = this.loadPowerTrend(defaultRange)
      const requestVersion = this.powerRequestVersion
      const detailRequest = getTieLineDetail(id)
        .then((res) => {
          if (requestVersion === this.powerRequestVersion && this.selectedId === id) {
            this.detail = res?.data || null
          }
        })
        .catch(() => {
          if (requestVersion === this.powerRequestVersion && this.selectedId === id) {
            this.detail = this.selectedLine
          }
        })
      await Promise.all([detailRequest, trendRequest])
    },
    setStartRegion(value) {
      this.activeStartRegion = value || ''
      this._dropSelectionIfHidden()
    },
    setEndRegion(value) {
      this.activeEndRegion = value || ''
      this._dropSelectionIfHidden()
    },
    setCapacityRange(minValue, maxValue) {
      let min = normalizeCapacityMw(minValue)
      let max = normalizeCapacityMw(maxValue)
      if (min !== null && max !== null && min > max) [min, max] = [max, min]
      this.activeMinCapacityMw = min
      this.activeMaxCapacityMw = max
      this._dropSelectionIfHidden()
    },
    setMinCapacityMw(value) {
      this.setCapacityRange(value, this.activeMaxCapacityMw)
    },
    setMaxCapacityMw(value) {
      this.setCapacityRange(this.activeMinCapacityMw, value)
    },
    swapRegions() {
      ;[this.activeStartRegion, this.activeEndRegion] = [
        this.activeEndRegion,
        this.activeStartRegion,
      ]
      this._dropSelectionIfHidden()
    },
    resetFilters() {
      this.activeStartRegion = ''
      this.activeEndRegion = ''
      this.activeMinCapacityMw = null
      this.activeMaxCapacityMw = null
    },
    clearSelection() {
      this._invalidatePowerRequests()
      this.selectedId = null
      this.detail = null
      this._clearPowerTrend()
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
