import request from '@/utils/request'
import { encrypt } from '@/utils/jsencrypt'

export function login(data) {
  const { username = '', password = '', code, uuid } = data || {}
  return request({
    url: '/gateway/ecenter/system/auth/login',
    method: 'post',
    headers: { isToken: false },
    data: {
      username: username.trim(),
      password: encrypt(password),
      code,
      uuid,
    },
  })
}

export function getCodeImg() {
  return request({
    url: '/gateway/code',
    method: 'get',
    headers: { isToken: false },
  })
}

export function logout() {
  return request({
    url: '/gateway/ecenter/system/auth/logout',
    method: 'post',
  })
}
