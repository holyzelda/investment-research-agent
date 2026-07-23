import { getToken, getUserIdentity } from '@/utils/auth'

function endpoint(path) {
  const base = import.meta.env.VITE_APP_BASE_API || '/gateway/ir-agent/'
  return `${base.replace(/\/$/, '')}${path}`
}

export async function streamReportEvents(reportTaskId, { signal, onEvent }) {
  const { userId, username } = getUserIdentity()
  const headers = { Accept: 'text/event-stream' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (userId) headers.userId = userId
  if (username) headers.username = encodeURIComponent(username)
  const response = await fetch(endpoint(`/ir/report-tasks/${reportTaskId}/events`), { headers, signal })
  if (!response.ok || !response.body) throw new Error(`报告进度连接失败 ${response.status}`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let event = 'message'
  let data = ''
  const dispatch = () => {
    if (data) onEvent({ type: event, data: JSON.parse(data) })
    event = 'message'
    data = ''
  }
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    let index
    while ((index = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, index).replace(/\r$/, '')
      buffer = buffer.slice(index + 1)
      if (!line) dispatch()
      else if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) data += line.slice(5).trim()
    }
    if (done) break
  }
}
