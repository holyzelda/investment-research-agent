const TOKEN_KEY = 'Admin-Token'
const USER_ID_KEY = 'ir-user-id'
const USERNAME_KEY = 'ir-username'
const LOGIN_REQUIRED_KEY = 'ir-login-required'

function getSessionStorage() {
  if (typeof window === 'undefined') return null
  return typeof window.sessionStorage?.getItem === 'function' ? window.sessionStorage : null
}

export function getToken() {
  if (typeof window === 'undefined') return ''
  if (typeof window.localStorage?.getItem !== 'function') return ''
  return window.localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (typeof window === 'undefined') return
  if (typeof window.localStorage?.setItem !== 'function') return
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  if (typeof window === 'undefined') return
  if (typeof window.localStorage?.removeItem !== 'function') return
  window.localStorage.removeItem(TOKEN_KEY)
}

function getLocalStorage() {
  if (typeof window === 'undefined') return null
  return typeof window.localStorage?.getItem === 'function' ? window.localStorage : null
}

export function getUserIdentity() {
  const storage = getLocalStorage()
  return {
    userId: storage?.getItem(USER_ID_KEY) || '',
    username: storage?.getItem(USERNAME_KEY) || '',
  }
}

export function setUserIdentity({ userId, username }) {
  const storage = getLocalStorage()
  if (!storage || !userId || !username) return
  storage.setItem(USER_ID_KEY, String(userId))
  storage.setItem(USERNAME_KEY, String(username))
}

export function removeUserIdentity() {
  const storage = getLocalStorage()
  storage?.removeItem(USER_ID_KEY)
  storage?.removeItem(USERNAME_KEY)
}

export function markLoginRequired() {
  getSessionStorage()?.setItem(LOGIN_REQUIRED_KEY, '1')
}

export function isLoginRequired() {
  return getSessionStorage()?.getItem(LOGIN_REQUIRED_KEY) === '1'
}

export function clearLoginRequired() {
  getSessionStorage()?.removeItem(LOGIN_REQUIRED_KEY)
}

export function takeTokenFromLocation() {
  if (typeof window === 'undefined') return ''
  const url = new URL(window.location.href)
  const token = url.searchParams.get('token') || url.searchParams.get('access_token') || ''
  if (!token) return ''

  url.searchParams.delete('token')
  url.searchParams.delete('access_token')
  window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`)
  setToken(token)
  return token
}
