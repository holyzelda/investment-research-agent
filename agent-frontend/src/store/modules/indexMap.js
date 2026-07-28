import { defineStore } from 'pinia'
import {
  getIndexMapOverview,
  getIndexMapProvinceDetail,
  listIndexMapPeriods,
} from '@/api/indexMap'

function payload(response) {
  return response?.data || response || null
}

export const useIndexMapStore = defineStore('indexMap', {
  state: () => ({
    periods: [],
    activePeriod: '',
    overview: null,
    selectedProvinceCode: '',
    provinceDetail: null,
    periodsLoading: false,
    overviewLoading: false,
    detailLoading: false,
    periodsError: '',
    overviewError: '',
    detailError: '',
    overviewRequestVersion: 0,
    detailRequestVersion: 0,
  }),
  actions: {
    async initialize() {
      this.periodsLoading = true
      this.periodsError = ''
      try {
        this.periods = payload(await listIndexMapPeriods())?.items || []
        if (!this.periods.length) return
        await this.selectPeriod(this.periods[0].period)
      } catch (error) {
        this.periodsError = '指数期次加载失败，请稍后重试'
      } finally {
        this.periodsLoading = false
      }
    },
    async selectPeriod(period) {
      if (!period) return
      const previousProvince = this.selectedProvinceCode
      this.activePeriod = period
      this.overviewRequestVersion += 1
      this.detailRequestVersion += 1
      const version = this.overviewRequestVersion
      this.overviewLoading = true
      this.overviewError = ''
      this.overview = null
      this.provinceDetail = null
      try {
        const overview = payload(await getIndexMapOverview(period))
        if (version !== this.overviewRequestVersion || this.activePeriod !== period) return
        this.overview = overview
        const keep = overview?.provinces?.some((item) => item.provinceCode === previousProvince)
        const selected = keep ? previousProvince : overview?.summary?.leader?.provinceCode
        this.selectedProvinceCode = selected || ''
        if (selected) await this._loadDetail(selected, period)
      } catch (error) {
        if (version === this.overviewRequestVersion && this.activePeriod === period) {
          this.overviewError = '全国指数加载失败，请稍后重试'
        }
      } finally {
        if (version === this.overviewRequestVersion && this.activePeriod === period) {
          this.overviewLoading = false
        }
      }
    },
    async selectProvince(provinceCode) {
      if (!provinceCode || !this.activePeriod) return
      this.selectedProvinceCode = provinceCode
      await this._loadDetail(provinceCode, this.activePeriod)
    },
    async _loadDetail(provinceCode, period) {
      this.detailRequestVersion += 1
      const version = this.detailRequestVersion
      this.detailLoading = true
      this.detailError = ''
      this.provinceDetail = null
      try {
        const detail = payload(await getIndexMapProvinceDetail(provinceCode, period))
        if (version === this.detailRequestVersion && this.activePeriod === period && this.selectedProvinceCode === provinceCode) {
          this.provinceDetail = detail
        }
      } catch (error) {
        if (version === this.detailRequestVersion && this.activePeriod === period && this.selectedProvinceCode === provinceCode) {
          this.detailError = '省份详情加载失败，请稍后重试'
        }
      } finally {
        if (version === this.detailRequestVersion && this.activePeriod === period && this.selectedProvinceCode === provinceCode) {
          this.detailLoading = false
        }
      }
    },
    async retryOverview() {
      await this.selectPeriod(this.activePeriod)
    },
    async retryDetail() {
      await this._loadDetail(this.selectedProvinceCode, this.activePeriod)
    },
  },
})
