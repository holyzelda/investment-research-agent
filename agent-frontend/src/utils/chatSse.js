import { getToken, getUserIdentity } from '@/utils/auth'
import { isRelogin } from '@/utils/request'
import { loginUrl } from '@/utils/appPath'
import { ElMessageBox } from 'element-plus'

function endpoint(path) {
  const base = import.meta.env.VITE_APP_BASE_API || '/gateway/ir-agent/'
  return `${base.replace(/\/$/, '')}${path}`
}

function authHeaders() {
  const { userId, username } = getUserIdentity()
  const headers = { 'Content-Type': 'application/json', Accept: 'text/event-stream' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (userId) headers.userId = userId
  if (username) headers.username = encodeURIComponent(username)
  return headers
}

function handleUnauthorized() {
  if (isRelogin.show) return
  isRelogin.show = true
  ElMessageBox.confirm('登录状态已失效，请重新登录', '登录状态异常', {
    confirmButtonText: '重新登录',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    isRelogin.show = false
    window.location.replace(loginUrl())
  }).catch(() => { isRelogin.show = false })
}

/**
 * 打开一条 POST-SSE 流。
 * @param {string} path - 接口路径，如 /ir/chat/diag
 * @param {object} body - 请求体
 * @param {{ onEvent: (e: {type:string, id:string|null, data:any}) => void, onOpen?: (info: {conversationId: string|null}) => void, onComplete?: (info: {reason: 'eof'|'aborted'|'transport-error'}) => void, signal?: AbortSignal }} opts
 * @returns {{ close: () => void }}
 */
export function openChatStream(path, body, {
  onEvent,
  onOpen,
  onComplete,
  signal: externalSignal,
} = {}) {
  const controller = new AbortController()
  let completed = false

  const complete = (reason) => {
    if (completed) return
    completed = true
    if (typeof onComplete === 'function') onComplete({ reason })
  }
  const abortFromExternal = () => controller.abort()
  if (externalSignal) externalSignal.addEventListener('abort', abortFromExternal, { once: true })

  async function run() {
    let response
    try {
      response = await fetch(endpoint(path), {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      })
    } catch (err) {
      if (err.name === 'AbortError') {
        complete('aborted')
        return
      }
      onEvent({ type: 'error', id: null, data: { code: 0, msg: '网络连接失败', data: null } })
      complete('transport-error')
      return
    }

    if (response.status === 401) {
      handleUnauthorized()
      onEvent({ type: 'error', id: null, data: { code: 401, msg: '登录状态已失效', data: null } })
      complete('transport-error')
      return
    }
    if (!response.ok || !response.body) {
      onEvent({ type: 'error', id: null, data: { code: response.status, msg: `连接失败 ${response.status}`, data: null } })
      complete('transport-error')
      return
    }

    if (typeof onOpen === 'function') {
      onOpen({ conversationId: response.headers.get('X-IR-Conversation-Id') })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let eventType = 'message'
    let eventId = null
    let dataLines = []

    function dispatch() {
      if (!dataLines.length) return
      const raw = dataLines.join('\n')
      let parsed
      try { parsed = JSON.parse(raw) } catch { parsed = raw }
      const fallbackType = parsed && typeof parsed === 'object'
        ? parsed.event || parsed.type
        : null
      onEvent({
        type: eventType === 'message' ? fallbackType || 'message' : eventType,
        id: eventId,
        data: parsed,
      })
      eventType = 'message'
      eventId = null
      dataLines = []
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        let idx
        while ((idx = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, idx).replace(/\r$/, '')
          buffer = buffer.slice(idx + 1)
          if (!line) {
            dispatch()
          } else if (line.startsWith('event:')) {
            eventType = line.slice(6).trim()
          } else if (line.startsWith('id:')) {
            eventId = line.slice(3).trim()
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart())
          }
        }
        if (done) {
          const finalLine = buffer.replace(/\r$/, '')
          if (finalLine.startsWith('event:')) eventType = finalLine.slice(6).trim()
          else if (finalLine.startsWith('id:')) eventId = finalLine.slice(3).trim()
          else if (finalLine.startsWith('data:')) dataLines.push(finalLine.slice(5).trimStart())
          dispatch()
          complete('eof')
          break
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        complete('aborted')
        return
      }
      onEvent({ type: 'error', id: null, data: { code: 0, msg: '流读取中断', data: null } })
      complete('transport-error')
    } finally {
      if (externalSignal) externalSignal.removeEventListener('abort', abortFromExternal)
    }
  }

  run()
  return { close: () => controller.abort() }
}
