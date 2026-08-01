import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const getUserInfo = vi.fn()
const setUserIdentity = vi.fn()
const removeUserIdentity = vi.fn()

vi.mock('@/api/session', () => ({ getUserInfo }))
vi.mock('@/api/auth', () => ({ login: vi.fn() }))
vi.mock('@/utils/auth', () => ({
  getToken: () => 'platform-token',
  setToken: vi.fn(),
  setUserIdentity,
  removeUserIdentity,
}))

const { useSessionStore } = await import('@/store/modules/session')

describe('session user information parsing', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getUserInfo.mockReset()
    setUserIdentity.mockReset()
    removeUserIdentity.mockReset()
  })

  it('stores normalized identity from the standard ecenter user wrapper', async () => {
    getUserInfo.mockResolvedValue({
      code: 200,
      data: { user: { userName: 'zhangsan', nickName: '张三', userId: 'u-1' } },
    })

    const store = useSessionStore()
    await expect(store.loadUserInfo({ force: true })).resolves.toBe(true)

    expect(store.username).toBe('zhangsan')
    expect(store.nickname).toBe('张三')
    expect(store.userId).toBe('u-1')
    expect(setUserIdentity).toHaveBeenCalledWith({ userId: 'u-1', username: 'zhangsan' })
  })

  it('supports lowercase nickname while keeping username as the request identity', async () => {
    getUserInfo.mockResolvedValue({
      code: 200,
      data: { data: { username: 'lisi', nickname: '李四', id: 'u-2' } },
    })

    const store = useSessionStore()
    await store.loadUserInfo({ force: true })

    expect(store.username).toBe('lisi')
    expect(store.nickname).toBe('李四')
    expect(store.userId).toBe('u-2')
    expect(setUserIdentity).toHaveBeenCalledWith({ userId: 'u-2', username: 'lisi' })
  })

  it('falls back to the nickname when ecenter omits a separate username', async () => {
    getUserInfo.mockResolvedValue({ code: 200, data: { user: { nickName: '王五', userId: 'u-3' } } })

    const store = useSessionStore()
    await store.loadUserInfo({ force: true })

    expect(store.username).toBe('王五')
    expect(store.nickname).toBe('王五')
    expect(setUserIdentity).toHaveBeenCalledWith({ userId: 'u-3', username: '王五' })
  })

  it('clears identity when ecenter does not return a complete user', async () => {
    getUserInfo.mockResolvedValue({ code: 200, data: { user: { userId: 'u-3' } } })

    const store = useSessionStore()
    await expect(store.loadUserInfo({ force: true })).resolves.toBe(false)

    expect(store.userId).toBeNull()
    expect(store.username).toBe('')
    expect(store.nickname).toBe('')
    expect(removeUserIdentity).toHaveBeenCalledOnce()
  })

  it('clears persisted identity on reset', () => {
    const store = useSessionStore()
    store.reset()

    expect(removeUserIdentity).toHaveBeenCalledOnce()
  })
})
