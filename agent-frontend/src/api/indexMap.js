import request from '@/utils/request'

export function listIndexMapPeriods() {
  return request({ url: '/ir/index-map/periods', method: 'get' })
}

export function getIndexMapOverview(period) {
  return request({ url: '/ir/index-map/overview', method: 'get', params: { period } })
}

export function getIndexMapProvinceDetail(provinceCode, period) {
  return request({
    url: `/ir/index-map/provinces/${provinceCode}`,
    method: 'get',
    params: { period },
  })
}
