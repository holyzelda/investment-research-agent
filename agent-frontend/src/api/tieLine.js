import request from '@/utils/request'

// 联络线地图 · 只读接口薄封装（响应壳由 utils/request 统一解包为 data）
export function getTieLines() {
  return request({
    url: '/ir/tie-lines',
    method: 'get',
  })
}

export function getTieLineDetail(lineId) {
  return request({
    url: `/ir/tie-lines/${lineId}`,
    method: 'get',
  })
}
