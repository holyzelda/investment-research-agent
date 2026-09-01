import request from '@/utils/request'

export function getLedgerUsers() {
  return request({ url: '/ir/calc/ledger/users', method: 'get' })
}

export function getLedgerProvinces() {
  return request({ url: '/ir/calc/ledger/provinces', method: 'get' })
}

export function getLedgerBootstrap(params) {
  return request({
    url: '/ir/calc/ledger/bootstrap',
    method: 'get',
    params,
    paramsSerializer: { indexes: null },
  })
}

export function getLedgerRecords(params) {
  return request({
    url: '/ir/calc/ledger',
    method: 'get',
    params,
    // FastAPI 的 list[str] Query 需要 province=甘肃&province=宁夏，
    // 不能使用 Axios 默认的 province[]=... 形式。
    // 发起人多选是单个逗号分隔参数，由调用方拼好后原样传。
    paramsSerializer: { indexes: null },
  })
}
