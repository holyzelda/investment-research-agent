import { defineStore } from 'pinia'
import {
  getConsultationStats,
  getConsultations,
  getMarketNews,
  submitConsultation,
} from '@/api/policyMarket'

export const usePolicyMarketStore = defineStore('policyMarket', {
  state: () => ({
    consultations: [],
    selectedConsultationId: null,
    consultationsLoading: false,
    consultationsError: '',
    submitting: false,
    submitError: '',
    news: [],
    newsLoading: false,
    newsError: '',
    statsFilters: { province: 'all', period: 'all', topic: 'all' },
    stats: { total: 0, trend: 0, rangeLabel: '全部省份' },
    statsLoading: false,
    statsError: '',
  }),

  getters: {
    selectedConsultation: (state) => state.consultations.find(
      (item) => item.id === state.selectedConsultationId,
    ) || null,
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
        if (!this.selectedConsultationId && records.length) {
          this.selectedConsultationId = records[0].id
        }
      } catch (error) {
        this.consultationsError = error?.message || '咨询记录加载失败'
        throw error
      } finally {
        this.consultationsLoading = false
      }
    },

    async loadNews() {
      this.newsLoading = true
      this.newsError = ''
      try {
        this.news = await getMarketNews()
      } catch (error) {
        this.newsError = error?.message || '市场资讯加载失败'
        throw error
      } finally {
        this.newsLoading = false
      }
    },

    async loadStats() {
      this.statsLoading = true
      this.statsError = ''
      try {
        this.stats = await getConsultationStats(this.statsFilters)
      } catch (error) {
        this.statsError = error?.message || '咨询统计加载失败'
        throw error
      } finally {
        this.statsLoading = false
      }
    },

    selectConsultation(id) {
      if (this.consultations.some((item) => item.id === id)) {
        this.selectedConsultationId = id
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
        id: pendingId,
        title: normalizedQuestion,
        question: normalizedQuestion,
        answer: '',
        status: 'processing',
        createdAt: new Date().toISOString(),
        sourceScope: [],
      }

      this.submitError = ''
      this.submitting = true
      this.consultations.unshift(pendingRecord)
      this.selectedConsultationId = pendingId

      try {
        const completedRecord = await submitConsultation({ question: normalizedQuestion })
        const index = this.consultations.findIndex((item) => item.id === pendingId)
        if (index !== -1) this.consultations.splice(index, 1, completedRecord)
        this.selectedConsultationId = completedRecord.id
        return completedRecord
      } catch (error) {
        const index = this.consultations.findIndex((item) => item.id === pendingId)
        if (index !== -1) {
          this.consultations.splice(index, 1, { ...pendingRecord, status: 'failed' })
        }
        this.submitError = error?.message || '咨询提交失败'
        throw error
      } finally {
        this.submitting = false
      }
    },

    async setStatsFilters(nextFilters) {
      this.statsFilters = { ...this.statsFilters, ...nextFilters }
      await this.loadStats()
    },
  },
})
