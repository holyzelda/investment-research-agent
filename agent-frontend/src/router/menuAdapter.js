const PLACEHOLDER_ICONS = new Set(['', '#', 'default'])
const PATH_ICON_MAP = {
  '/home': 'home',
  '/ir': 'home',
  '/calculation': 'calculation',
}

export function joinRoutePath(parentPath = '', childPath = '') {
  if (!childPath) return parentPath || '/'
  if (/^https?:\/\//i.test(childPath)) return childPath
  if (childPath.startsWith('/')) return childPath
  const base = parentPath && parentPath !== '/' ? parentPath.replace(/\/$/, '') : ''
  return `${base}/${childPath}`.replace(/\/+/g, '/')
}

function isHidden(route) {
  return route?.hidden === true || route?.meta?.hidden === true
}

function normalizePath(path = '') {
  return path.startsWith('/') ? path : `/${path}`
}

function resolveIcon(route = {}) {
  const icon = route.meta?.icon || route.icon || ''
  return PLACEHOLDER_ICONS.has(icon) ? (PATH_ICON_MAP[normalizePath(route.path)] || 'default') : icon
}

function normalizeRoute(rawRoute, loadView, parentPath = '') {
  const route = { ...rawRoute }
  const fullPath = joinRoutePath(parentPath, route.path || '')
  const children = Array.isArray(route.children)
    ? route.children
        .filter((child) => !isHidden(child))
        .map((child) => normalizeRoute(child, loadView, fullPath))
        .filter(Boolean)
    : []

  const normalized = {
    path: route.path || fullPath,
    name: route.name,
    redirect: route.redirect,
    hidden: route.hidden,
    meta: { ...(route.meta || {}), icon: resolveIcon(route) },
  }

  if (route.component === 'Layout' || route.component === 'ParentView') {
    if (children.length) normalized.children = children
    if (!normalized.redirect && children.length) normalized.redirect = joinRoutePath(fullPath, children[0].path)
    return normalized
  }

  if (route.component === 'InnerLink') {
    normalized.meta = { ...normalized.meta, link: route.path }
  } else if (route.component) {
    const view = loadView(route.component)
    if (!view && !children.length) return null
    normalized.component = view || undefined
  }

  if (children.length) normalized.children = children
  if (!normalized.component && !normalized.children?.length) return null
  return normalized
}

export function filterBackendRoutes(routes = [], loadView) {
  return routes
    .filter((route) => !isHidden(route))
    .flatMap((source) => {
      const route = normalizeRoute(source, loadView)
      if (!route) return []
      if (source.component === 'Layout' && source.path === '/') return route.children || []
      return [route]
    })
}

export function buildRailRoutes(routes = []) {
  return routes
    .filter((route) => !isHidden(route))
    .map((route) => ({
      path: normalizePath(route.path),
      title: route.meta?.title || route.title || route.name || route.path,
      icon: route.meta?.icon || resolveIcon(route),
    }))
    .filter((item) => item.path && item.title)
}
