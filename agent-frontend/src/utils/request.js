import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一请求实例
// 说明（平台接入）：本系统不做登录。用户在统一平台完成登录，平台/网关向后端请求头注入身份；
// 前端仅经网关基地址发起请求，无需附带任何登录 token。
const service = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || '/gateway/',
  timeout: 60 * 1000,
  // 同域部署，携带平台会话 cookie（如平台以 cookie 承载会话）
  withCredentials: true,
})

// 请求拦截器：仅设置通用头，不处理登录 token
service.interceptors.request.use(
  (config) => {
    config.headers['Content-Type'] = config.headers['Content-Type'] || 'application/json;charset=utf-8'
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
    // 平台负责登录鉴权；本系统收到 401 视为平台会话问题，提示由平台处理
    if (code === 401) {
      ElMessage.error('登录状态异常，请返回平台首页重新进入')
      return Promise.reject(new Error(msg || '未授权'))
    }
    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  },
  (error) => {
    let message = error.message
    const backendMsg = error.response?.data?.msg
    if (backendMsg) message = backendMsg
    else if (message === 'Network Error') message = '后端接口连接异常'
    else if (message?.includes('timeout')) message = '系统接口请求超时'
    else if (message?.includes('Request failed with status code')) {
      message = `系统接口异常 ${message.slice(-3)}`
    }
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default service
