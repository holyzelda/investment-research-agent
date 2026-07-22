import { defineStore } from 'pinia'
import { getUserInfo } from '@/api/session'
import { getToken } from '@/utils/auth'

// 会话状态：当前用户来自平台注入（后端读 header 后经 /ir/me 下发）。
export const useSessionStore = defineStore('session', {
  state: () => ({
    token: getToken(),
    userId: null,
    username: '',
    loaded: false,
  }),
  actions: {
    async loadUserInfo({ force = false } = {}) {
      if (this.loaded && !force) return Boolean(this.username)
      this.token = getToken()
      if (!this.token) {
        this.username = this.username || '访客'
        this.loaded = true
        return false
      }
      try {
        const res = await getUserInfo()
        const data = res?.data || {}
        const user = data.user || data.sysUser || data
        this.userId = data.userId ?? data.user_id ?? user.userId ?? user.id ?? null
        this.username = data.username || data.userName || user.userName || user.nickName || '访客'
        return true
      } catch (e) {
        // 平台身份缺失时降级为访客（开发态），不阻塞对话首页
        this.username = this.username || '访客'
        return false
      } finally {
        this.loaded = true
      }
    },
    reset() {
      this.token = ''
      this.userId = null
      this.username = ''
      this.loaded = false
    },
  },
})
