import request from '@/utils/request'
import { encrypt } from '@/utils/jsencrypt'

export function login(data) {
  const { username = '', password = '', code, uuid, captchaToken } = data || {}
  const captcha = captchaToken ? { captchaToken } : { code, uuid }
  return request({
    url: '/gateway/ecenter/system/auth/login',
    method: 'post',
    headers: { isToken: false },
    data: {
      username: username.trim(),
      password: encrypt(password),
      ...captcha,
    },
  })
}

export function createCaptchaChallenge({ scene = 'password_login', preferredMode = 'image_selection' } = {}) {
  return request({
    __silentError: true,
    url: '/gateway/ecenter/system/auth/captcha/challenges',
    method: 'post',
    headers: { isToken: false },
    data: { scene, preferredMode },
  })
}

export function verifyCaptchaChallenge(challengeId, tileIds) {
  return request({
    __silentError: true,
    url: `/gateway/ecenter/system/auth/captcha/challenges/${encodeURIComponent(challengeId)}/verify`,
    method: 'post',
    headers: { isToken: false },
    data: { tileIds: [...new Set(tileIds)] },
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
