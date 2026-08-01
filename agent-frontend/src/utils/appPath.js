const APP_BASE_URL = import.meta.env.BASE_URL || '/'
const APP_BASE_PATH = APP_BASE_URL === '/' ? '' : APP_BASE_URL.replace(/\/$/, '')

export function appUrl(path = '/') {
  const relativePath = String(path).replace(/^\/+/, '')
  return relativePath ? `${APP_BASE_URL}${relativePath}` : APP_BASE_URL
}

export function currentRouteLocation(location = window.location) {
  const pathname = location.pathname || '/'
  const routePath = APP_BASE_PATH && (pathname === APP_BASE_PATH || pathname.startsWith(`${APP_BASE_PATH}/`))
    ? pathname.slice(APP_BASE_PATH.length) || '/'
    : pathname
  return `${routePath}${location.search || ''}${location.hash || ''}`
}

export function loginUrl(location = window.location) {
  const current = currentRouteLocation(location)
  const redirect = current && current !== '/login' ? `?redirect=${encodeURIComponent(current)}` : ''
  return appUrl(`/login${redirect}`)
}
