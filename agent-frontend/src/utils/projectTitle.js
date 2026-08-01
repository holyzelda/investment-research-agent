import { formatNumber } from './formatNumber'

const REGION_DISPLAY_NAMES = {
  浙江: '浙江省',
  上海: '上海市',
  广东: '广东省',
  江苏: '江苏省',
  湖南: '湖南省',
  深圳: '深圳市',
  海南: '海南省',
  重庆: '重庆市',
  河南: '河南省',
  安徽: '安徽省',
  湖北: '湖北省',
  天津: '天津市',
  四川: '四川省',
  陕西: '陕西省',
  贵州: '贵州省',
  辽宁: '辽宁省',
  吉林: '吉林省',
  山东: '山东省',
  黑龙江: '黑龙江省',
  山西: '山西省',
  福建: '福建省',
  江西: '江西省',
  新疆: '新疆维吾尔自治区',
  冀北: '冀北',
  河北南网: '河北南网',
  蒙东: '蒙东',
  青海: '青海省',
  云南: '云南省',
  北京: '北京市',
  广西: '广西壮族自治区',
  宁夏: '宁夏回族自治区',
  蒙西: '蒙西',
  甘肃: '甘肃省',
  西藏: '西藏自治区',
  冀南: '冀南',
}

export function normalizeProjectRegion(region) {
  const value = String(region ?? '').trim()
  return REGION_DISPLAY_NAMES[value] || value
}

export function formatProjectLocation(region, nodeName) {
  const rawRegion = String(region ?? '').trim()
  const displayRegion = normalizeProjectRegion(rawRegion)
  let displayNode = String(nodeName ?? '').trim()
  const prefixes = [...new Set([displayRegion, rawRegion])]
    .filter(Boolean)
    .sort((left, right) => right.length - left.length)
  const repeatedPrefix = prefixes.find((prefix) => displayNode.startsWith(prefix))
  if (repeatedPrefix) displayNode = displayNode.slice(repeatedPrefix.length).trimStart()
  return `${displayRegion}${displayNode}`
}

export function formatProjectScale(power, capacity) {
  if (power === null || power === undefined || capacity === null || capacity === undefined) return ''
  return `${formatNumber(power)}MW/${formatNumber(capacity)}MWh`
}

export function buildResultTitle(region, nodeName) {
  return `${formatProjectLocation(region, nodeName)}储能项目测算结果`
}

export function buildReportTitle(region, nodeName, power, capacity) {
  return `${formatProjectLocation(region, nodeName)}${formatProjectScale(power, capacity)}储能项目报告`
}

export function buildReportProjectName(region, nodeName, power, capacity) {
  return `${formatProjectLocation(region, nodeName)}${formatProjectScale(power, capacity)}独立储能项目`
}

export function buildVersionTitle(region, nodeName, power, capacity) {
  return [`测算${formatProjectLocation(region, nodeName)}`, formatProjectScale(power, capacity)]
    .filter(Boolean)
    .join(' ')
}
