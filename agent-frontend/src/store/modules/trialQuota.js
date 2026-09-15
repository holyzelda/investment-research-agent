import { defineStore } from 'pinia'
import { getTrialQuota } from '@/api/trialQuota'

export const useTrialQuotaStore = defineStore('trialQuota', {
  state: () => ({
    quota: null,
    loading: false,
    error: '',
  }),

  getters: {
    isTrial: (state) => state.quota?.isTrial === true,
  },

  actions: {
    async load() {
      if (this.loading) return this.quota
      this.loading = true
      this.error = ''
      try {
        this.quota = await getTrialQuota()
        return this.quota
      } catch (error) {
        this.error = error?.message || '试用额度加载失败'
        throw error
      } finally {
        this.loading = false
      }
    },

    async refresh() {
      try {
        return await this.load()
      } catch {
        return null
      }
    },

    reset() {
      this.quota = null
      this.loading = false
      this.error = ''
    },
  },
})