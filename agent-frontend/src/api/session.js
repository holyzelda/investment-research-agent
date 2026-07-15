import request from '@/utils/request'

// 当前登录用户信息：后端从平台注入的请求头解析 user_id/username 后下发。
// 本系统不做登录，此接口仅用于在界面上展示"当前用户"。
export function getUserInfo() {
  return request({
    url: '/ir/me',
    method: 'get',
  })
}
