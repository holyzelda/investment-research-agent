import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getToken, getUserIdentity, markLoginRequired, removeToken, removeUserIdentity } from '@/utils/auth'
import { loginUrl } from '@/utils/appPath'

// 统一请求实例
// 说明（平台接入）：支持独立登录，也支持统一平台携带 Token 直接承接；
// 前端仅经网关基地址发起请求，Token 统一由拦截器转发。
const service = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || '/gateway/ir-agent/',
  timeout: 60 * 1000,
  // 同域部署，携带平台会话 cookie（如平台以 cookie 承载会话）
  withCredentials: true,
})

const ROOT_GATEWAY_PREFIXES = ['/gateway/code', '/gateway/ecenter/']

export function usesRootGateway(url = '') {
  return ROOT_GATEWAY_PREFIXES.some((prefix) => url.startsWith(prefix))
}

export const isRelogin = { show: false }

function redirectToLogin() {
  if (typeof window === 'undefined') return
  window.location.replace(loginUrl())
}

function handleUnauthorized(config, message) {
  if (config?.__skipAuthRedirect || config?.headers?.isToken === false) return false

  removeToken()
  removeUserIdentity()
  markLoginRequired()
  if (!isRelogin.show) {
    isRelogin.show = true
    ElMessageBox.confirm(
      message || '登录状态已失效，请重新登录',
      '登录状态异常',
      {
        confirmButtonText: '重新登录',
        cancelButtonText: '取消',
        type: 'warning',
      },
    ).then(() => {
      isRelogin.show = false
      redirectToLogin()
    }).catch(() => {
      isRelogin.show = false
    })
  }
  return true
}

// 请求拦截器：附带平台 Token；IR 业务请求同时携带 ecenter 已解析的身份。
service.interceptors.request.use(
  (config) => {
    if (usesRootGateway(config.url)) config.baseURL = ''
    config.__skipAuthRedirect = config.headers?.isToken === false
    config.headers['Content-Type'] = config.headers['Content-Type'] || 'application/json;charset=utf-8'
    const token = getToken()
    if (token && config.headers.isToken !== false) {
      config.headers.Authorization = config.headers.Authorization || `Bearer ${token}`
    }
    if (!usesRootGateway(config.url)) {
      const { userId, username } = getUserIdentity()
      if (userId && !config.headers.userId) config.headers.userId = userId
      if (username && !config.headers.username) config.headers.username = encodeURIComponent(username)
    }
    delete config.headers.isToken
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：按 {code,msg,data} 响应壳解析
service.interceptors.response.use(
  (res) => {
    // 二进制直接返回
    const responseType = res.request?.responseType
    if (responseType === 'blob' || responseType === 'arraybuffer') {
      return res.data
    }
    const body = res.data ?? {}
    const code = body.code ?? 200
    const msg = body.msg || '系统未知错误'

    if (code === 200) {
      return body
    }
    if (code === 401) {
      handleUnauthorized(res.config, msg)
      return Promise.reject(new Error(msg || '未授权'))
    }
    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  },
  (error) => {
    if (error.response?.status === 401) {
      const message = error.response?.data?.msg || '登录状态已失效，请重新登录'
      handleUnauthorized(error.config, message)
    }
    let message = error.message
    const backendMsg = error.response?.data?.msg
    if (backendMsg) message = backendMsg
    else if (message === 'Network Error') message = '后端接口连接异常'
    else if (message?.includes('timeout')) message = '系统接口请求超时'
    else if (message?.includes('Request failed with status code')) {
      message = `系统接口异常 ${message.slice(-3)}`
    }
    if (error.response?.status !== 401) ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default service
