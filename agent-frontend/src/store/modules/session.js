import { defineStore } from 'pinia'
import { login as loginRequest } from '@/api/auth'
import { getUserInfo } from '@/api/session'
import { getToken, removeUserIdentity, setToken, setUserIdentity } from '@/utils/auth'

function flattenObjects(value, result = [], seen = new Set()) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || seen.has(value)) return result
  seen.add(value)
  result.push(value)
  for (const key of ['data', 'user', 'userInfo', 'sysUser', 'profile']) {
    flattenObjects(value[key], result, seen)
  }
  return result
}

function firstField(objects, fields) {
  for (const object of objects) {
    for (const field of fields) {
      const value = object[field]
      if (value !== undefined && value !== null && String(value).trim() !== '') return value
    }
  }
  return null
}

// 会话状态：当前用户来自 ecenter getInfo。
export const useSessionStore = defineStore('session', {
  state: () => ({
    token: getToken(),
    userId: null,
    username: '',
    nickname: '',
    loaded: false,
  }),
  actions: {
    async login(form) {
      const res = await loginRequest(form)
      const data = res?.data || {}
      const token = data.access_token || data.token
      if (!token) throw new Error('登录成功但未返回 Token')
      setToken(token)
      removeUserIdentity()
      this.token = token
      this.userId = null
      this.username = ''
      this.nickname = ''
      this.loaded = false
      return data
    },
    async loadUserInfo({ force = false } = {}) {
      if (this.loaded && !force) return Boolean(this.username)
      this.token = getToken()
      if (!this.token) {
        this.userId = null
        this.username = ''
        this.nickname = ''
        removeUserIdentity()
        this.loaded = true
        return false
      }
      try {
        const res = await getUserInfo()
        const objects = flattenObjects(res)
        const userId = firstField(objects, ['userId', 'user_id', 'userid', 'id'])
        const username = firstField(objects, ['username', 'userName'])
          || firstField(objects, ['nickname', 'nickName', 'name', 'realName'])
        const nickname = firstField(objects, ['nickname', 'nickName']) || username
        if (!userId || !username) throw new Error('未获取到完整用户身份')
        this.userId = userId
        this.username = username
        this.nickname = nickname
        setUserIdentity({ userId, username })
        return true
      } catch (e) {
        this.userId = null
        this.username = ''
        this.nickname = ''
        removeUserIdentity()
        return false
      } finally {
        this.loaded = true
      }
    },
    reset() {
      this.token = ''
      this.userId = null
      this.username = ''
      this.nickname = ''
      this.loaded = false
      removeUserIdentity()
    },
  },
})
