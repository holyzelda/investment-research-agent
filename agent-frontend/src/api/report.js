import request from '@/utils/request'

export function createReport(taskId) {
  return request({ url: `/ir/calc/tasks/${taskId}/report`, method: 'post' })
}

export function getReportTask(reportTaskId) {
  return request({ url: `/ir/report-tasks/${reportTaskId}`, method: 'get' })
}

export function getReport(reportId) {
  return request({ url: `/ir/reports/${reportId}`, method: 'get' })
}
