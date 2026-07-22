import router from '@/router'
import { clearLoginRequired, getToken, isLoginRequired, removeToken, setToken, takeTokenFromLocation } from '@/utils/auth'
import { useSessionStore } from '@/store/modules/session'
import { usePermissionStore } from '@/store/modules/permission'

let openerTokenPromise = null
let openerTokenRequested = false

function requestOpenerToken() {
  if (typeof window === 'undefined' || !window.opener) return Promise.resolve(false)
  if (openerTokenRequested) return Promise.resolve(false)
  if (openerTokenPromise) return openerTokenPromise
  openerTokenRequested = true

  openerTokenPromise = new Promise((resolve) => {
    let settled = false
    const finish = (received) => {
      if (settled) return
      settled = true
      window.removeEventListener('message', onMessage)
      resolve(received)
    }
    const onMessage = (event) => {
      const message = event.data
      if (message?.type !== 'token' || !message.token) return
      setToken(message.token)
      clearLoginRequired()
      finish(true)
    }
    window.addEventListener('message', onMessage)
    window.opener.postMessage('request-token', '*')
    window.setTimeout(() => finish(false), 5000)
  })
  return openerTokenPromise
}

async function registerBackendRoutes(permissionStore) {
  const routes = await permissionStore.generateRoutes()
  routes.forEach((route) => {
    if (route.name && router.hasRoute(route.name)) return
    const routePath = route.path.startsWith('/') ? route.path : `/${route.path}`
    if (router.getRoutes().some((current) => current.path === routePath)) return
    router.addRoute('Root', route)
  })
}

router.beforeEach(async (to) => {
  const locationToken = takeTokenFromLocation()
  const loginRequired = isLoginRequired()
  if (locationToken) openerTokenRequested = true

  // 401 后的手动登录不再从 opener 重新取旧 Token。
  if (to.path === '/login' && loginRequired) openerTokenRequested = true

  const canRequestOpenerToken = to.path !== '/login' || !loginRequired
  if (!locationToken && canRequestOpenerToken && typeof window !== 'undefined' && window.opener) {
    const received = await requestOpenerToken()
    if (received) return { ...to, replace: true }
  }

  if (to.path === '/login') {
    return getToken() && !isLoginRequired() ? { path: '/home', replace: true } : true
  }

  const sessionStore = useSessionStore()
  const permissionStore = usePermissionStore()

  if (getToken() && !sessionStore.loaded) {
    const loaded = await sessionStore.loadUserInfo({ force: true })
    if (!loaded) removeToken()
  }

  if (!permissionStore.loaded) {
    if (!getToken()) {
      permissionStore.loaded = true
      return true
    }
    try {
      await registerBackendRoutes(permissionStore)
      return { ...to, replace: true }
    } catch (error) {
      console.warn('[permission] 菜单加载失败，保留当前页面：', error)
    }
  }

  return true
})
