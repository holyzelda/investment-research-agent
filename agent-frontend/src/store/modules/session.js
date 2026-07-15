import { defineStore } from 'pinia'
import { getUserInfo } from '@/api/session'

// 会话状态：当前用户来自平台注入（后端读 header 后经 /ir/me 下发）。
// 本系统不做登录，故无 login/logout/token 逻辑。
export const useSessionStore = defineStore('session', {
  state: () => ({
    userId: null,
    username: '',
    loaded: false,
  }),
  actions: {
    async loadUserInfo() {
      try {
        const res = await getUserInfo()
        const data = res.data || {}
        this.userId = data.userId ?? data.user_id ?? null
        this.username = data.username || data.userName || '访客'
      } catch (e) {
        // 平台身份缺失时降级为访客（开发态），不阻塞对话首页
        this.username = this.username || '访客'
      } finally {
        this.loaded = true
      }
    },
  },
})
