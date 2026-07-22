import request from '@/utils/request'

export function getRouters(params = {}) {
  return request({
    url: '/gateway/ecenter/system/menu/getRouters/eAgentIr',
    method: 'get',
    params: {
      systemSign: 'eAgentIr',
      ...params,
    },
  })
}
