import { defineStore } from 'pinia'
import {
  getConsultation,
  getConsultations,
  getMarketNews,
  getMarketOverview,
  submitConsultation,
} from '@/api/policyMarket'

const DEFAULT_FILTERS = { province: 'all', period: 'all', topic: 'all' }
const DEFAULT_STATS = { total: 0, trendPercent: null, rangeLabel: '全部省份 · 全部时间' }

export const usePolicyMarketStore = defineStore('policyMarket', {
  state: () => ({
    consultations: [],
    selectedConsultationId: null,
    consultationsLoading: false,
    consultationsError: '',
    consultationDetails: {},
    consultationDetailLoading: false,
    consultationDetailError: '',
    submitting: false,
    submitError: '',
    news: [],
    newsLoading: false,
    newsError: '',
    statsFilters: { ...DEFAULT_FILTERS },
    stats: { ...DEFAULT_STATS },
    topicOptions: [],
    statsLoading: false,
    statsError: '',
    overviewRequestId: 0,
    newsRequestId: 0,
  }),

  getters: {
    selectedConsultation: (state) => state.consultationDetails[state.selectedConsultationId]
      || state.consultations.find((item) => item.id === state.selectedConsultationId)
      || null,
  },

  actions: {
    async loadInitialData() {
      await Promise.allSettled([
        this.loadConsultations(),
        this.loadNews(),
        this.loadStats(),
      ])
    },

    async loadConsultations() {
      this.consultationsLoading = true
      this.consultationsError = ''
      try {
        const records = await getConsultations()
        this.consultations = records
        if (!this.selectedConsultationId && records.length) this.selectedConsultationId = records[0].id
      } catch (error) {
        this.consultationsError = error?.message || '咨询记录加载失败'
        throw error
      } finally {
        this.consultationsLoading = false
      }
    },

    async loadNews(filters = this.statsFilters) {
      const requestId = ++this.newsRequestId
      this.newsLoading = true
      this.newsError = ''
      try {
        const records = await getMarketNews(filters)
        if (requestId !== this.newsRequestId) return
        this.news = records
      } catch (error) {
        if (requestId === this.newsRequestId) {
          this.newsError = error?.message || '市场资讯加载失败'
          throw error
        }
      } finally {
        if (requestId === this.newsRequestId) this.newsLoading = false
      }
    },

    async loadStats() {
      const requestId = ++this.overviewRequestId
      this.statsLoading = true
      this.statsError = ''
      try {
        const overview = await getMarketOverview(this.statsFilters)
        if (requestId !== this.overviewRequestId) return
        this.stats = {
          total: overview.total,
          trendPercent: overview.trendPercent,
          rangeLabel: overview.rangeLabel,
        }
        this.topicOptions = overview.topicOptions || []
      } catch (error) {
        if (requestId === this.overviewRequestId) {
          this.statsError = error?.message || '资讯概览加载失败'
          throw error
        }
      } finally {
        if (requestId === this.overviewRequestId) this.statsLoading = false
      }
    },

    async selectConsultation(id) {
      if (!this.consultations.some((item) => item.id === id)) return
      this.selectedConsultationId = id
      if (this.consultationDetails[id]) return

      this.consultationDetailLoading = true
      this.consultationDetailError = ''
      try {
        const detail = await getConsultation(id)
        this.consultationDetails[id] = detail
      } catch (error) {
        this.consultationDetailError = error?.message || '咨询详情加载失败'
        throw error
      } finally {
        this.consultationDetailLoading = false
      }
    },

    startNewConsultation() {
      this.selectedConsultationId = null
      this.submitError = ''
    },

    async submitQuestion(question) {
      const normalizedQuestion = String(question || '').trim()
      if (!normalizedQuestion) throw new Error('请输入政策或市场问题')
      const pendingId = `pending-${Date.now()}`
      const pendingRecord = {
        id: pendingId, title: normalizedQuestion, question: normalizedQuestion, answer: '', status: 'processing',
        createdAt: new Date().toISOString(), sourceData: null,
      }
      this.submitError = ''
      this.submitting = true
      this.consultations.unshift(pendingRecord)
      this.selectedConsultationId = pendingId
      try {
        const completedRecord = await submitConsultation({ question: normalizedQuestion })
        const index = this.consultations.findIndex((item) => item.id === pendingId)
        if (index !== -1) this.consultations.splice(index, 1, completedRecord)
        this.consultationDetails[completedRecord.id] = completedRecord
        this.selectedConsultationId = completedRecord.id
        try {
          await this.loadConsultations()
        } catch {
          // 已有完整结果可展示；历史列表刷新失败不覆盖成功咨询。
        }
        return completedRecord
      } catch (error) {
        const index = this.consultations.findIndex((item) => item.id === pendingId)
        if (index !== -1) this.consultations.splice(index, 1, { ...pendingRecord, status: 'failed' })
        this.submitError = error?.message || '咨询提交失败'
        throw error
      } finally {
        this.submitting = false
      }
    },

    async setStatsFilters(nextFilters) {
      const filters = { ...this.statsFilters, ...nextFilters }
      this.statsFilters = filters
      await this.loadStats()
      if (filters.topic !== 'all' && !this.topicOptions.some((item) => item.value === filters.topic)) {
        this.statsFilters = { ...this.statsFilters, topic: 'all' }
        await this.loadStats()
      }
      await this.loadNews(this.statsFilters)
    },
  },
})
