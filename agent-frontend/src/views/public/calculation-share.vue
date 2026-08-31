<template>
  <div class="ir-share-page">
    <!-- 加载态 -->
    <div v-if="loading" class="ir-share-page__centered">
      <div class="ir-share-page__spinner" />
      <p class="ir-share-page__hint">正在加载分享内容…</p>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="ir-share-page__centered">
      <h1 class="ir-share-page__title ir-share-page__title--error">无法查看</h1>
      <p class="ir-share-page__desc">{{ error }}</p>
    </div>

    <!-- 已过期 / 已撤销 -->
    <div v-else-if="share.status === 'expired'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享链接已过期</h1>
      <p class="ir-share-page__desc">该测算结果分享链接已超过有效期，请联系分享者重新分享。</p>
    </div>
    <div v-else-if="share.status === 'revoked'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享已撤销</h1>
      <p class="ir-share-page__desc">分享者已撤销此分享链接，无法继续查看。</p>
    </div>
    <div v-else-if="share.status === 'not_found'" class="ir-share-page__centered">
      <h1 class="ir-share-page__title">分享不存在</h1>
      <p class="ir-share-page__desc">该分享链接无效，请检查链接是否正确。</p>
    </div>

    <!-- 有效分享内容 -->
    <div v-else-if="share.status === 'active'" class="ir-share-page__content">
      <!-- 结果卡片 -->
      <div class="ir-share-result">
        <ReportWatermark />
        <!-- 横幅 -->
        <div class="ir-share-result__banner" :style="{ backgroundImage: `url(${bannerBg})` }">
          <div class="ir-share-result__banner-mask" />
          <div class="ir-share-result__banner-status">
            <span class="ir-share-result__ok">测算完成 ✓</span>
            <span v-if="share.version" class="ir-share-result__ver">{{ share.version }}</span>
          </div>
          <div class="ir-share-result__banner-body">
            <h1 class="ir-share-result__banner-title">{{ bannerTitle }}</h1>
            <p class="ir-share-result__banner-sub">
              测算时间 {{ calculatedAtText }}
              <span v-if="share.version"> · 版本 {{ share.version }}</span>
            </p>
          </div>
        </div>

        <!-- 基础信息 -->
        <section v-if="share.basicInfo" class="ir-share-block">
          <h2 class="ir-share-block__title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <path d="M4 20V9l8-5 8 5v11" stroke-linejoin="round" />
              <path d="M9 20v-6h6v6M8 10h.01M16 10h.01" stroke-linecap="round" />
            </svg>
            项目基础边界条件
          </h2>
          <div class="ir-share-basic">
            <div v-for="m in basicMetrics" :key="m.key" class="ir-share-basic__stat">
              <span class="ir-share-basic__k">
                <svg class="ir-share-basic__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" v-html="m.icon" />
                {{ m.label }}
              </span>
              <span class="ir-share-basic__v xc-num" :class="{ 'ir-share-basic__v--accent': m.accent }">
                {{ m.text }}<span v-if="m.unit" class="ir-share-basic__unit">{{ m.unit }}</span>
              </span>
            </div>
          </div>
        </section>

        <!-- 核心财务指标 -->
        <section v-if="share.financial" class="ir-share-module">
          <FinancialBlock :financial="share.financial" />
        </section>

        <!-- 图表 -->
        <section class="ir-share-charts">
          <RevenueDonut :donut="share.advanced?.donut || {}" />
          <DebtServiceCoverage :coverage="share.advanced?.debtServiceCoverage || {}" />
        </section>

        <!-- 警告 -->
        <div v-if="warnings.length" class="ir-share-warn">
          <span v-for="(w, i) in warnings" :key="i">⚠ {{ w }}</span>
        </div>

        <!-- 页脚 -->
        <div class="ir-share-result__footer">
          <span class="ir-share-result__footer-brand">西安奇点能源股份有限公司</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPublicShare } from '@/api/calc'
import { formatNumber, formatPrice } from '@/utils/formatNumber'
import { buildResultTitle } from '@/utils/projectTitle'
import FinancialBlock from '@/views/home/components/FinancialBlock.vue'
import RevenueDonut from '@/views/home/components/RevenueDonut.vue'
import DebtServiceCoverage from '@/views/home/components/DebtServiceCoverage.vue'
import ReportWatermark from '@/views/report/components/ReportWatermark.vue'
import bannerBg from '@/assets/home-welcome-background.png'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const share = ref({})

const ICON_POWER = '<path d="M13 2 4 14h7l-1 8 9-12h-7z" stroke-linejoin="round" stroke-linecap="round"/>'
const ICON_CAPACITY = '<rect x="4" y="7" width="14" height="10" rx="2"/><path d="M20 10v4" stroke-linecap="round"/>'
const ICON_CHARGE = '<path d="M12 3v6m0 0 3-3m-3 3L9 6" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="11" width="14" height="10" rx="2"/>'
const ICON_DISCHARGE = '<path d="M12 21v-6m0 0 3 3m-3-3-3 3" stroke-linecap="round" stroke-linejoin="round"/><rect x="5" y="3" width="14" height="10" rx="2"/>'
const ICON_LOSS = '<circle cx="12" cy="12" r="9"/><path d="M8 12h8" stroke-linecap="round"/>'

// 基础信息映射
const basicMetrics = computed(() => {
  const b = share.value.basicInfo || {}
  const priceText = (value) => (value == null ? '待完善' : formatPrice(value))
  return [
    { key: 'powerMw', label: '装机功率', text: formatNumber(b.powerMw), unit: 'MW', accent: true, icon: ICON_POWER },
    { key: 'capacityMwh', label: '装机容量', text: formatNumber(b.capacityMwh), unit: 'MWh', accent: true, icon: ICON_CAPACITY },
    { key: 'actualSpread', label: '实际价差', text: priceText(b.actualSpread), unit: '元/kWh', accent: false, icon: ICON_LOSS },
    { key: 'chargeCost', label: '充电成本', text: priceText(b.chargeCost), unit: '元/kWh', accent: false, icon: ICON_CHARGE },
    { key: 'dischargeReturn', label: '放电返还', text: priceText(b.dischargeReturn), unit: '元/kWh', accent: false, icon: ICON_DISCHARGE },
    { key: 'lossCost', label: '损耗费用', text: priceText(b.lossCost), unit: '元/kWh', accent: false, icon: ICON_LOSS },
  ]
})

const bannerTitle = computed(() => buildResultTitle(
  share.value.basicInfo?.province,
  share.value.basicInfo?.nodeName,
  share.value.basicInfo?.city,
))

const calculatedAtText = computed(() => {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/.exec(share.value.calculatedAt || '')
  if (!m) return '—'
  const [, y, mo, d, hh, mm, ss] = m
  return `${y}年${mo}月${d}日 ${hh}:${mm}:${ss}`
})

const warnings = computed(() => share.value.warnings || [])

// 加载分享数据
async function loadShare() {
  const shareCode = route.params.shareCode
  if (!shareCode) {
    error.value = '分享链接无效'
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await getPublicShare(shareCode)
    const data = response?.data?.data || response?.data
    if (!data?.status) throw new Error('分享接口未返回有效内容')
    share.value = data
  } catch (err) {
    const status = err?.response?.status
    if (status === 404) {
      share.value = { status: 'not_found' }
    } else {
      error.value = err?.response?.data?.msg || err?.message || '加载分享内容失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadShare()
})
</script>

<style scoped>
/* ── 页面容器 ── */
.ir-share-page {
  min-height: 100vh;
  background: #0a0e1a;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* ── 居中状态 ── */
.ir-share-page__centered {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--xc-space-4);
  padding: var(--xc-space-8);
  text-align: center;
  max-width: 480px;
}
.ir-share-page__title {
  margin: 0;
  font-size: var(--xc-fs-h2);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-bold);
}
.ir-share-page__title--error {
  color: var(--xc-status-danger);
}
.ir-share-page__desc {
  margin: 0;
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  line-height: var(--xc-lh-normal);
}
.ir-share-page__hint {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-sm);
}
.ir-share-page__spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--xc-border-soft);
  border-top-color: var(--xc-accent-blue);
  border-radius: 50%;
  animation: ir-spin 0.8s linear infinite;
}
@keyframes ir-spin { to { transform: rotate(360deg); } }

/* ── 内容区 ── */
.ir-share-page__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 860px;
  padding: var(--xc-space-7) var(--xc-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
}

/* ── 结果卡片 ── */
.ir-share-result {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-5);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-sm);
  background: linear-gradient(180deg, rgba(3, 8, 22, 0.97) 0%, rgba(8, 14, 30, 0.97) 100%);
  box-shadow: var(--xc-shadow-raised);
  overflow: hidden;
}
.ir-share-result > :not(.ir-report-watermark) {
  position: relative;
  z-index: 1;
}
.ir-share-result :deep(.ir-report-watermark) {
  z-index: 2;
  color: rgba(219, 235, 255, 0.075);
  font-size: 12px;
  font-weight: var(--xc-fw-medium);
}

/* 横幅 */
.ir-share-result__banner {
  position: relative;
  display: flex;
  align-items: center;
  min-height: clamp(140px, 16vw, 200px);
  border-radius: var(--xc-radius-sm) var(--xc-radius-sm) 0 0;
  background-color: #010515;
  background-position: right center;
  background-size: 66% auto;
  background-repeat: no-repeat;
  overflow: hidden;
}
.ir-share-result__banner-status {
  position: absolute;
  z-index: 1;
  top: var(--xc-space-5);
  left: var(--xc-space-7);
  display: flex;
  align-items: center;
  gap: var(--xc-space-4);
}
.ir-share-result__ok {
  font-size: var(--xc-fs-base);
  color: var(--xc-status-ok);
  font-weight: var(--xc-fw-semi);
}
.ir-share-result__ver {
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-inverse);
  background: var(--xc-accent-blue);
  border-radius: var(--xc-radius-full);
  padding: 1px var(--xc-space-3);
}
.ir-share-result__banner-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(3, 8, 22, 0.85) 0%, rgba(3, 8, 22, 0.45) 42%, rgba(3, 8, 22, 0) 68%);
}
.ir-share-result__banner-body {
  position: relative;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--xc-space-2);
  padding: var(--xc-space-7);
}
.ir-share-result__banner-title {
  margin: 0;
  font-size: var(--xc-fs-h3);
  font-weight: var(--xc-fw-bold);
  color: var(--xc-text-strong);
}
.ir-share-result__banner-sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--xc-space-2);
  margin: 0;
  font-size: var(--xc-fs-2xs);
  color: var(--xc-text-soft);
}

/* 通用区块 */
.ir-share-block {
  padding: var(--xc-space-7);
  margin: 0 var(--xc-space-6);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
  overflow: hidden;
}
.ir-share-block__title {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  font-size: var(--xc-fs-md);
  color: var(--xc-text-strong);
  font-weight: var(--xc-fw-semi);
  margin: 0 0 var(--xc-space-5);
}
.ir-share-block__title svg { width: 18px; height: 18px; flex: 0 0 auto; color: var(--xc-accent-blue); }

/* 基础信息 */
.ir-share-basic {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--xc-space-5);
}
.ir-share-basic__stat {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-2);
}
.ir-share-basic__k {
  display: flex;
  align-items: center;
  gap: var(--xc-space-2);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-2xs);
}
.ir-share-basic__icon { width: 14px; height: 14px; flex-shrink: 0; }
.ir-share-basic__v {
  color: var(--xc-text-strong);
  font-size: var(--xc-fs-lg);
  font-weight: var(--xc-fw-bold);
  font-variant-numeric: tabular-nums;
}
.ir-share-basic__v--accent { color: var(--xc-accent-purple); }
.ir-share-basic__unit {
  margin-left: 2px;
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
  font-weight: var(--xc-fw-regular);
}

.ir-share-module {
  container-type: inline-size;
  margin: 0 var(--xc-space-6);
  border: 1px solid var(--xc-border-card);
  border-radius: var(--xc-radius-lg);
  background: var(--xc-surface-card);
  box-shadow: var(--xc-shadow-sm);
  overflow: hidden;
}

/* 图表 */
.ir-share-charts {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: var(--xc-space-6);
  margin: 0 var(--xc-space-6);
}
.ir-share-charts > * {
  min-width: 0;
  container-type: inline-size;
}

/* 警告 */
.ir-share-warn {
  display: flex;
  flex-direction: column;
  gap: var(--xc-space-2);
  padding: 0 var(--xc-space-6);
  font-size: var(--xc-fs-xs);
  color: var(--xc-status-warn);
}

/* 页脚 */
.ir-share-result__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: var(--xc-space-3) var(--xc-space-6);
  border-top: 1px solid var(--xc-border-soft);
  background: var(--xc-surface-tinted);
}
.ir-share-result__footer-brand {
  color: var(--xc-text-mute);
  font-size: var(--xc-fs-2xs);
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .ir-share-page__content { padding: var(--xc-space-4); }
  .ir-share-basic {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--xc-space-4);
  }
  .ir-share-charts { grid-template-columns: 1fr; }
  .ir-share-block { margin: 0 var(--xc-space-4); }
  .ir-share-module { margin: 0 var(--xc-space-4); }
  .ir-share-charts { margin: 0 var(--xc-space-4); }
  .ir-share-warn { padding: 0 var(--xc-space-4); }
  .ir-share-result__banner { min-height: 160px; }
  .ir-share-result__banner-body { padding: var(--xc-space-5); }
  .ir-share-result__banner-status { top: var(--xc-space-3); left: var(--xc-space-5); }
}
@media (max-width: 480px) {
  .ir-share-page__content { padding: var(--xc-space-3); }
  .ir-share-basic {
    grid-template-columns: 1fr 1fr;
    gap: var(--xc-space-3);
  }
  .ir-share-block { padding: var(--xc-space-5); margin: 0 var(--xc-space-3); }
  .ir-share-module { margin: 0 var(--xc-space-3); }
  .ir-share-charts { margin: 0 var(--xc-space-3); }
  .ir-share-warn { padding: 0 var(--xc-space-3); }
  .ir-share-basic__v { font-size: var(--xc-fs-md); }
}
</style>
