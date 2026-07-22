import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const getUserInfo = vi.fn()

vi.mock('@/api/session', () => ({ getUserInfo }))
vi.mock('@/api/auth', () => ({ login: vi.fn() }))
vi.mock('@/utils/auth', () => ({
  getToken: () => 'platform-token',
  setToken: vi.fn(),
}))

const { useSessionStore } = await import('@/store/modules/session')

describe('session user information parsing', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getUserInfo.mockReset()
  })

  it('shows userName from the standard ecenter user wrapper', async () => {
    getUserInfo.mockResolvedValue({
      code: 200,
      data: { user: { userName: '张三', userId: 'u-1' } },
    })

    const store = useSessionStore()
    await expect(store.loadUserInfo({ force: true })).resolves.toBe(true)

    expect(store.username).toBe('张三')
    expect(store.userId).toBe('u-1')
  })

  it('unwraps an additional data layer and supports nickName/name fallbacks', async () => {
    getUserInfo.mockResolvedValue({
      code: 200,
      data: { data: { nickName: '李四', id: 'u-2' } },
    })

    const store = useSessionStore()
    await store.loadUserInfo({ force: true })

    expect(store.username).toBe('李四')
    expect(store.userId).toBe('u-2')
  })
})
