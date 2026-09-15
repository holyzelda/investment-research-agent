import request from '@/utils/request'

export function getTrialQuota() {
  return request({ url: '/ir/trial/quota', method: 'get' }).then((response) => response.data)
}