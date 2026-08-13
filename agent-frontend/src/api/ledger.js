import request from '@/utils/request'

export function getLedgerProvinces() {
  return request({ url: '/ir/calc/ledger/provinces', method: 'get' })
}

export function getLedgerRecords(params) {
  return request({
    url: '/ir/calc/ledger',
    method: 'get',
    params,
    // FastAPI 的 list[str] Query 需要 province=甘肃&province=宁夏，
    // 不能使用 Axios 默认的 province[]=... 形式。
    paramsSerializer: { indexes: null },
  })
}
