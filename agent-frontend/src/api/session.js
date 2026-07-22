import request from '@/utils/request'

// 当前用户信息：平台 Token 由请求拦截器转发给 ecenter。
export function getUserInfo() {
  return request({
    url: '/gateway/ecenter/system/user/getInfo',
    method: 'get',
    params: { systemSign: 'eAgentIr' },
  })
}
