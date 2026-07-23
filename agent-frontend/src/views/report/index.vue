<template>
  <main class="ir-report-page">
    <nav class="ir-report-actions" aria-label="报告操作">
      <el-button class="ir-report-actions__button" aria-label="返回" @click="router.back()">
        <span class="ir-report-actions__icon" aria-hidden="true">←</span>
        <span class="ir-report-actions__label">返回</span>
      </el-button>
      <el-button class="ir-report-actions__button is-active" aria-label="下载 PDF" @click="printReport">
        <span class="ir-report-actions__icon" aria-hidden="true">↓</span>
        <span class="ir-report-actions__label">下载 PDF</span>
      </el-button>
      <el-button class="ir-report-actions__button" aria-label="分享报告" @click="shareReport">
        <span class="ir-report-actions__icon" aria-hidden="true">↗</span>
        <span class="ir-report-actions__label">分享</span>
      </el-button>
    </nav>
    <article v-if="report" class="ir-report-document">
      <header class="ir-report-cover">
        <p>储能项目测算方案</p>
        <h1>{{ report.title }}</h1>
        <p>编制日期：{{ report.generatedDate }}</p>
      </header>
      <section>
        <h2>一、项目基本信息</h2>
        <table>
          <tbody>
            <tr><th>项目省份</th><td>{{ report.project?.province }}</td><th>节点</th><td>{{ report.project?.nodeName }}</td></tr>
            <tr><th>功率</th><td>{{ report.project?.powerMw }} MW</td><th>容量</th><td>{{ report.project?.capacityMwh }} MWh</td></tr>
            <tr><th>储能时长</th><td>{{ report.project?.durationHours }} 小时</td><th>项目类型</th><td>{{ report.project?.projectType }}</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <h2>二、市场与政策环境</h2>
        <h3>2.1 市场状态及项目影响</h3>
        <table><tbody><tr v-for="(value, name) in report.policyEnvironment?.marketStatus" :key="name"><th>{{ name }}</th><td>{{ value }}</td><td>{{ report.policyEnvironment?.projectImpact?.[name] || report.missingDataText }}</td></tr></tbody></table>
      </section>
      <section>
        <h2>三、测算结果</h2>
        <pre>{{ report.calculation?.result }}</pre>
      </section>
      <section>
        <h2>四、图表数据</h2>
        <p>运营期：{{ report.charts?.operationYears }} 年</p>
        <table><tbody><tr v-for="(series, name) in report.charts?.series" :key="name"><th>{{ name }}</th><td>{{ series?.join('、') }}</td></tr></tbody></table>
      </section>
      <section>
        <h2>五、智能分析</h2>
        <div v-for="(section, key) in report.aiSections" :key="key" class="ir-report-ai"><h3>{{ key }}</h3><p>{{ section.text }}</p></div>
      </section>
    </article>
    <el-empty v-else-if="loaded" description="报告不存在" />
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport } from '@/api/report'

const route = useRoute()
const router = useRouter()
const report = ref(null)
const loaded = ref(false)

onMounted(async () => {
  try { report.value = (await getReport(route.params.reportId)).data || null } finally { loaded.value = true }
})
function printReport() { window.print() }

async function shareReport() {
  const shareData = {
    title: report.value?.title || '储能项目测算方案',
    text: report.value?.title || '储能项目测算方案',
    url: window.location.href,
  }
  if (navigator.share) {
    try {
      await navigator.share(shareData)
    } catch (error) {
      if (error?.name !== 'AbortError') throw error
    }
    return
  }
  await navigator.clipboard?.writeText(shareData.url)
}
</script>

<style scoped>
.ir-report-page { min-height: 100%; overflow: auto; padding: var(--xc-space-6); background: var(--xc-surface-base); color: var(--xc-text-default); }
.ir-report-actions {
  position: fixed;
  z-index: 10;
  right: 34px;
  top: 50%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transform: translateY(-50%);
}
.ir-report-actions__button.el-button {
  width: 58px;
  height: 58px;
  margin: 0;
  padding: 0;
  justify-content: flex-start;
  overflow: hidden;
  border: 0;
  border-radius: 18px;
  background: var(--xc-surface-glass);
  box-shadow: 0 10px 35px rgba(0, 0, 0, 0.35);
  color: var(--xc-text-soft);
  font-size: var(--xc-fs-sm);
  font-weight: var(--xc-fw-medium);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: width 0.28s ease, background 0.28s ease, color 0.2s ease;
}
.ir-report-actions__button.el-button.is-active {
  background: linear-gradient(135deg, #5675ff, #7657ff);
  color: var(--xc-text-inverse);
}
.ir-report-actions__button.el-button:hover,
.ir-report-actions__button.el-button:focus-visible {
  width: 170px;
  background: rgba(87, 110, 255, 0.18);
  color: var(--xc-text-strong);
}
.ir-report-actions__button.el-button:focus-visible {
  outline: 2px solid var(--xc-accent-blue);
  outline-offset: 3px;
}
.ir-report-actions__icon {
  display: inline-grid;
  flex: 0 0 58px;
  width: 58px;
  place-items: center;
  color: currentColor;
  font-size: 24px;
  line-height: 1;
}
.ir-report-actions__label {
  flex: 0 0 auto;
  opacity: 0;
  white-space: nowrap;
  transform: translateX(8px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.ir-report-actions__button.el-button:hover .ir-report-actions__label,
.ir-report-actions__button.el-button:focus-visible .ir-report-actions__label {
  opacity: 1;
  transform: translateX(0);
}
@media (prefers-reduced-motion: reduce) {
  .ir-report-actions__button.el-button,
  .ir-report-actions__label { transition: none; }
}
@media (max-width: 900px) {
  .ir-report-actions { right: var(--xc-space-4); top: auto; bottom: var(--xc-space-4); flex-direction: row; transform: none; }
  .ir-report-actions__button.el-button:hover,
  .ir-report-actions__button.el-button:focus-visible { width: 58px; }
  .ir-report-actions__button.el-button:hover .ir-report-actions__label,
  .ir-report-actions__button.el-button:focus-visible .ir-report-actions__label { display: none; }
}
.ir-report-document { width: 210mm; min-height: 297mm; box-sizing: border-box; margin: auto; padding: 25.4mm 31.75mm; background: var(--xc-surface-raised); color: var(--xc-text-default); font-family: serif; line-height: 1.75; }
.ir-report-cover { min-height: 150mm; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
h1 { font-size: 28px; } h2 { margin-top: 36px; border-bottom: 1px solid var(--xc-border-line); } h3 { margin-top: 20px; } table { width: 100%; border-collapse: collapse; } th, td { border: 1px solid var(--xc-border-line); padding: 6px 8px; text-align: left; } pre { white-space: pre-wrap; font-family: inherit; }
</style>
