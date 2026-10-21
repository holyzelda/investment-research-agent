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

// ecenter 手机验证码登录接口。国家区号固定为中国大陆，避免客户端传入任意地区。
export function sendSmsCode(mobile) {
  return request({
    url: '/gateway/ecenter/system/auth/sms/send',
    method: 'post',
    headers: { isToken: false },
    data: { mobile: String(mobile || '').trim(), countryCode: '86', scene: 'login' },
  })
}

export function loginBySms(data) {
  const { mobile = '', code = '', requestId } = data || {}
  return request({
    url: '/gateway/ecenter/system/auth/sms/login',
    method: 'post',
    headers: { isToken: false },
    data: {
      mobile: mobile.trim(),
      code: code.trim(),
      requestId,
      countryCode: '86',
    },
  })
}

export function logout() {
  return request({
    url: '/gateway/ecenter/system/auth/logout',
    method: 'post',
  })
}
