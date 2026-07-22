const TOKEN_KEY = 'Admin-Token'

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
