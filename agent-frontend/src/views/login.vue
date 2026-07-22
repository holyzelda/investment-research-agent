<template>
  <div class="login-stage" :style="{ '--login-bg-image': `url(${loginBackgroundUrl})` }">
    <main
      class="login-page"
      :style="{ transform: `translate(-50%, -50%) scale(${pageScale})` }"
    >
    <div class="login-canvas">

    <header class="brand-bar">
      <div class="brand-logo">
        <img :src="loginLogoUrl" alt="eTrader" />
      </div>
      <div class="brand-text">
        <strong>eTrader 2.0</strong>
        <span>玄策电力交易智慧决策平台</span>
      </div>
    </header>

    <nav class="top-nav" aria-label="顶部导航">
      <a href="javascript:void(0)">
        <MegaphoneIcon aria-hidden="true" />
        市场公告
      </a>
      <a href="javascript:void(0)">
        <ShieldCheckIcon aria-hidden="true" />
        安全保障
      </a>
      <a href="javascript:void(0)">
        <HeadphonesIcon aria-hidden="true" />
        帮助中心
      </a>
      <button class="lang-btn" type="button">
        简体中文
        <ChevronDownIcon aria-hidden="true" />
      </button>
    </nav>

    <section class="hero" aria-label="平台介绍">
      <h1 class="hero-title">
        <span>玄策电力交易智慧决策</span>
        <span>平台</span>
      </h1>
      <p class="hero-sub">让稳定的<em>清洁电力</em> 惠及每一个人</p>

      <div class="feature-row">
        <article v-for="feature in features" :key="feature.title" class="feature-item">
          <span class="feature-icon">
            <component :is="feature.icon" aria-hidden="true" />
          </span>
          <strong>{{ feature.title }}</strong>
          <em>{{ feature.desc }}</em>
        </article>
      </div>
    </section>

    <section class="market-card glass-card" aria-label="实时电力现货行情">
      <header class="market-head">
        <h3>实时电力现货行情</h3>
        <div class="market-time">
          <span>{{ marketTime }}</span>
          <RefreshCwIcon aria-hidden="true" />
        </div>
      </header>
      <div class="market-metrics">
        <article v-for="metric in metrics" :key="metric.label" class="metric-item">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </article>
      </div>
      <div ref="lineChartRef" class="market-chart"></div>
    </section>

    <section class="login-card glass-card" aria-label="用户登录">
      <header>
        <UserRoundIcon aria-hidden="true" />
        <h2>用户登录</h2>
      </header>

      <form class="login-form" @submit.prevent="onLogin">
        <label>
          <UserIcon aria-hidden="true" />
          <input v-model="form.username" type="text" autocomplete="username" placeholder="请输入账号" />
        </label>
        <label>
          <LockKeyholeIcon aria-hidden="true" />
          <input
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
          <button class="ghost-eye" type="button" @click="showPassword = !showPassword">
            <component :is="showPassword ? EyeIcon : EyeOffIcon" aria-hidden="true" />
          </button>
        </label>
        <div v-if="captchaEnabled" class="captcha-row">
          <label class="captcha-field">
            <ShieldCheckIcon aria-hidden="true" />
            <input v-model="form.code" type="text" autocomplete="off" maxlength="6" placeholder="请输入验证码" />
          </label>
          <button
            class="captcha-image"
            :class="{ 'is-error': captchaError }"
            type="button"
            aria-label="刷新验证码"
            @click="getCode"
          >
            <img v-if="codeUrl && !captchaError" :src="codeUrl" alt="验证码" @error="captchaError = true" />
            <span v-else class="captcha-refresh">
              <RefreshCwIcon aria-hidden="true" />
              点击刷新
            </span>
          </button>
        </div>

        <div class="form-tools">
          <label>
            <input v-model="rememberMe" type="checkbox" />
            <span>记住我</span>
          </label>
          <a href="javascript:void(0)">忘记密码?</a>
        </div>

        <button class="login-submit" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录平台' }}
        </button>
      </form>

      <div class="login-divider">
        <span>登录安全.全程守护</span>
      </div>

      <div class="security-row">
        <span v-for="auth in authMethods" :key="auth.label">
          <component :is="auth.icon" aria-hidden="true" />
          {{ auth.label }}
        </span>
      </div>
    </section>

    <section class="notice-card glass-card" aria-label="市场公告">
      <header class="notice-head">
        <h3>市场公告</h3>
        <a href="javascript:void(0)">
          更多
          <ChevronRightIcon aria-hidden="true" />
        </a>
      </header>
      <ul class="notice-list">
        <li v-for="notice in notices" :key="notice.title">
          <span class="notice-dot" aria-hidden="true"></span>
          <span class="notice-title">{{ notice.title }}</span>
          <span class="notice-date">{{ notice.date }}</span>
        </li>
      </ul>
    </section>

    <footer class="login-footer">
      <div>
        <span>专注</span>
        <i></i>
        <span>精进</span>
        <i></i>
        <span>开放</span>
        <i></i>
        <span>贡献</span>
      </div>
      <p>
        西安玄策电力交易中心 版权所有 © 2026
        <a href="https://beian.miit.gov.cn/#/Integrated/recordQuery" target="_blank" rel="noopener noreferrer">
          陕ICP备20010223号-3
        </a>
      </p>
    </footer>
    </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  ChevronDown as ChevronDownIcon,
  ChevronRight as ChevronRightIcon,
  Droplets as DropletsIcon,
  Eye as EyeIcon,
  EyeOff as EyeOffIcon,
  Headphones as HeadphonesIcon,
  KeyRound as KeyRoundIcon,
  LockKeyhole as LockKeyholeIcon,
  Megaphone as MegaphoneIcon,
  RefreshCw as RefreshCwIcon,
  Settings2 as Settings2Icon,
  ShieldCheck as ShieldCheckIcon,
  TrendingUp as TrendingUpIcon,
  User as UserIcon,
  UserRound as UserRoundIcon,
  Zap as ZapIcon,
} from '@lucide/vue'
import { useSessionStore } from '@/store/modules/session'
import { usePermissionStore } from '@/store/modules/permission'
import { getCodeImg } from '@/api/auth'
import { clearLoginRequired } from '@/utils/auth'
import loginBackgroundUrl from '@/assets/images/login_bg.png'
import loginLogoUrl from '@/assets/images/eTrader_logo2.png'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()
const permission = usePermissionStore()
const loading = ref(false)
const showPassword = ref(false)
const rememberMe = ref(true)
const lineChartRef = ref(null)
const codeUrl = ref('')
const captchaEnabled = ref(true)
const captchaError = ref(false)
const pageScale = ref(1)
const form = reactive({ username: '', password: '', code: '', uuid: '' })
let lineChart = null
let resizeObserver = null

const marketTime = '2026-06-01 10:30:00'

const features = [
  { icon: ZapIcon, title: '电力现货交易', desc: '高效透明' },
  { icon: DropletsIcon, title: '智慧决策分析', desc: '精准洞察' },
  { icon: TrendingUpIcon, title: '清洁能源消纳', desc: '绿色低碳' },
  { icon: ShieldCheckIcon, title: '安全高效运行', desc: '稳定可靠' },
]

const metrics = [
  { label: '实时价格(元/MWh)', value: '256.35' },
  { label: '实时负荷(MW)', value: '18,653' },
  { label: '新能源出力(MW)', value: '6,512' },
]

const authMethods = [
  { icon: ShieldCheckIcon, label: '统一身份认证' },
  { icon: KeyRoundIcon, label: '安全会话' },
  { icon: Settings2Icon, label: '权限动态管控' },
]

const notices = [
  { title: '关于开展蒙西电力现货市场日前结算试运行的公告', date: '2026-05-30' },
  { title: '蒙西电力现货市场结算细则修订说明', date: '2026-05-28' },
  { title: '关于清洁能源消纳保障机制的通知', date: '2026-05-25' },
]

const DESIGN_WIDTH = 2560
const DESIGN_HEIGHT = 1440

function updateScale() {
  pageScale.value = Math.min(window.innerWidth / DESIGN_WIDTH, window.innerHeight / DESIGN_HEIGHT)
}

async function getCode() {
  captchaError.value = false
  try {
    const res = await getCodeImg()
    captchaEnabled.value = res?.captchaEnabled === undefined ? true : res.captchaEnabled
    if (captchaEnabled.value) {
      if (!res?.img) throw new Error('验证码为空')
      codeUrl.value = `data:image/gif;base64,${res.img}`
      form.uuid = res.uuid
    }
  } catch (error) {
    captchaError.value = true
    codeUrl.value = ''
    ElMessage.error(error.message || '验证码获取失败')
  }
}

function initCharts() {
  if (lineChartRef.value) {
    lineChart = echarts.init(lineChartRef.value, null, { renderer: 'svg' })
    lineChart.setOption({
      animation: true,
      grid: { left: 4, right: 4, top: 8, bottom: 4 },
      xAxis: {
        type: 'category',
        show: false,
        boundaryGap: false,
        data: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '24:00'],
      },
      yAxis: { type: 'value', show: false, scale: true },
      series: [
        {
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: [210, 228, 240, 233, 248, 262, 255, 268, 256],
          lineStyle: { width: 2.2, color: '#4d9bff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(77,155,255,.38)' },
              { offset: 1, color: 'rgba(77,155,255,0)' },
            ]),
          },
        },
      ],
    })
  }
}

async function onLogin() {
  if (captchaEnabled.value && !form.code) {
    ElMessage.warning('请输入验证码')
    return
  }
  loading.value = true
  try {
    await session.login(form)
    clearLoginRequired()
    permission.resetRoutes()
    try {
      await session.loadUserInfo({ force: true })
    } catch (infoError) {
      console.warn('[login] 用户信息加载失败：', infoError)
    }
    router.push(route.query.redirect || '/home')
  } catch (error) {
    ElMessage.error(error.message || '登录失败')
    getCode()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  updateScale()
  window.addEventListener('resize', updateScale)
  getCode()
  await nextTick()
  initCharts()
  resizeObserver = new ResizeObserver(() => {
    lineChart?.resize()
  })
  if (lineChartRef.value) resizeObserver.observe(lineChartRef.value)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateScale)
  resizeObserver?.disconnect()
  lineChart?.dispose()
})
</script>

<style scoped>
:global(body) {
  margin: 0;
  background: #050b1a;
}

.login-stage {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background-color: #050b1a;
  background-image:
    linear-gradient(90deg, rgba(4, 10, 26, 0.35), rgba(4, 10, 26, 0.05) 42%, rgba(4, 10, 26, 0.28)),
    var(--login-bg-image);
  background-size: cover, cover;
  background-position: center, center;
  background-repeat: no-repeat;
}

.login-page {
  --cyan: #35d0ff;
  --blue: #2f7bff;
  --blue-light: #4d9bff;
  --text: #eaf3ff;
  --muted: rgba(206, 224, 250, 0.72);
  --faint: rgba(206, 224, 250, 0.5);
  --panel-bg: rgba(11, 27, 56, 0.55);
  --line: rgba(96, 150, 240, 0.2);
  --shadow: 0 18px 60px rgba(2, 10, 30, 0.4);
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2560px;
  height: 1440px;
  padding: 0;
  transform-origin: center center;
  color: var(--text);
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}

/* 内容层：按 1920×1080 版式定位，等比放大铺满 2560×1440 画布 */
.login-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  transform-origin: top left;
  transform: scale(1.33333);
}

/* ---------- 品牌 ---------- */
.brand-bar {
  position: absolute;
  top: 44px;
  left: 30px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
}

.brand-logo img {
  width: 54px;
  height: 54px;
  object-fit: contain;
  filter: drop-shadow(0 0 16px rgba(47, 123, 255, 0.55));
}

.brand-text strong {
  display: block;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.brand-text span {
  display: block;
  margin-top: 4px;
  color: rgba(224, 236, 255, 0.82);
  font-size: 16px;
}

/* ---------- 顶部导航 ---------- */
.top-nav {
  position: absolute;
  top: 52px;
  right: 30px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 24px;
}

.top-nav a,
.lang-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: rgba(224, 236, 255, 0.86);
  font-size: 16px;
  text-decoration: none;
  transition: color 0.2s ease, border-color 0.2s ease;
}

.top-nav a {
  padding-right: 24px;
  border-right: 1px solid rgba(255, 255, 255, 0.16);
}

.top-nav a:hover,
.lang-btn:hover {
  color: var(--cyan);
}

.top-nav svg,
.login-card header svg,
.security-row svg,
.feature-icon svg {
  width: 22px;
  height: 22px;
  stroke-width: 1.8;
}

.lang-btn {
  height: 44px;
  padding: 0 20px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
}

.lang-btn svg {
  width: 18px;
  height: 18px;
}

/* ---------- 左侧主视觉 ---------- */
.hero {
  position: absolute;
  top: 120px;
  left: 30px;
  width: 820px;
  z-index: 3;
}

.hero-title {
  margin: 0;
  font-size: 58px;
  font-weight: 600;
  line-height: 1.24;
  letter-spacing: 2px;
  text-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}

.hero-title span {
  display: block;
}

.hero-sub {
  margin: 26px 0 0;
  color: rgba(226, 238, 255, 0.9);
  font-size: 26px;
  letter-spacing: 1px;
}

.hero-sub em {
  color: var(--cyan);
  font-style: normal;
  text-shadow: 0 0 20px rgba(53, 208, 255, 0.4);
}

.feature-row {
  display: flex;
  gap: 46px;
  margin-top: 38px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.feature-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  margin-bottom: 14px;
  color: var(--cyan);
  background: linear-gradient(160deg, rgba(53, 208, 255, 0.22), rgba(47, 123, 255, 0.12));
  border: 1px solid rgba(77, 155, 255, 0.4);
  clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);
}

.feature-icon svg {
  width: 26px;
  height: 26px;
  filter: drop-shadow(0 0 10px rgba(53, 208, 255, 0.5));
}

.feature-item strong {
  font-size: 19px;
  font-weight: 600;
}

.feature-item em {
  margin-top: 6px;
  color: var(--muted);
  font-size: 14px;
  font-style: normal;
}

/* ---------- 玻璃卡片通用 ---------- */
.glass-card {
  border-radius: 16px;
  background: var(--panel-bg);
  backdrop-filter: blur(18px);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

/* ---------- 实时行情卡片 ---------- */
.market-card {
  position: absolute;
  left: 30px;
  top: 680px;
  width: 660px;
  box-sizing: border-box;
  padding: 22px 26px 16px;
  z-index: 4;
}

.market-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.market-head h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.market-time {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 14px;
}

.market-time svg {
  width: 18px;
  height: 18px;
  color: var(--blue-light);
  cursor: pointer;
}

.market-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-item span {
  color: var(--muted);
  font-size: 13px;
}

.metric-item strong {
  color: var(--cyan);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}

.market-chart {
  width: 100%;
  height: 64px;
  margin-top: 14px;
}

/* ---------- 登录卡片 ---------- */
.login-card {
  position: absolute;
  top: 145px;
  right: 30px;
  width: 560px;
  box-sizing: border-box;
  padding: 34px 40px 32px;
  border-radius: 20px;
  z-index: 4;
}

.login-card header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.login-card header svg {
  color: var(--blue-light);
}

.login-card header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
}

.login-form {
  display: grid;
  gap: 18px;
}

.login-form label {
  position: relative;
  display: flex;
  align-items: center;
}

.login-form label > svg {
  position: absolute;
  left: 18px;
  width: 20px;
  height: 20px;
  color: rgba(206, 224, 250, 0.7);
  z-index: 1;
}

.login-form input {
  width: 100%;
  height: 54px;
  box-sizing: border-box;
  border: 1px solid rgba(96, 150, 240, 0.22);
  border-radius: 12px;
  outline: none;
  background: rgba(6, 16, 38, 0.5);
  color: var(--text);
  padding: 0 48px 0 52px;
  font-size: 15px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.login-form input:focus {
  border-color: rgba(77, 155, 255, 0.6);
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.14);
}

.login-form input::placeholder {
  color: rgba(206, 224, 250, 0.42);
}

.ghost-eye {
  position: absolute;
  right: 16px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  background: transparent;
  color: rgba(206, 224, 250, 0.72);
  cursor: pointer;
}

.ghost-eye svg {
  width: 20px;
  height: 20px;
}

.captcha-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 122px;
  gap: 12px;
  align-items: center;
}

.captcha-field input {
  padding-right: 18px;
}

.captcha-image {
  display: block;
  width: 122px;
  height: 54px;
  padding: 0;
  border: 1px solid rgba(96, 150, 240, 0.28);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(6, 16, 38, 0.5);
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.captcha-image:hover {
  border-color: rgba(77, 155, 255, 0.55);
}

.captcha-image img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.captcha-image.is-error {
  border-style: dashed;
  border-color: rgba(255, 118, 132, 0.55);
}

.captcha-refresh {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  color: rgba(255, 150, 162, 0.92);
  font-size: 12px;
  white-space: nowrap;
}

.captcha-refresh svg {
  width: 16px;
  height: 16px;
  stroke-width: 2;
}

.form-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tools label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 14px;
  cursor: pointer;
}

.form-tools input {
  width: 16px;
  height: 16px;
  accent-color: var(--blue);
}

.form-tools a {
  color: var(--blue-light);
  font-size: 14px;
  text-decoration: none;
}

.login-submit {
  height: 56px;
  margin-top: 4px;
  border: 0;
  border-radius: 12px;
  background: linear-gradient(90deg, #3d8bff, #2f6fe6);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(47, 123, 255, 0.32);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.login-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 38px rgba(47, 123, 255, 0.46);
}

.login-submit:disabled {
  cursor: wait;
  opacity: 0.72;
}

.login-divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
  margin: 30px 0 22px;
  color: var(--muted);
  font-size: 14px;
}

.login-divider::before,
.login-divider::after {
  content: "";
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(96, 150, 240, 0.36));
}

.login-divider::after {
  background: linear-gradient(90deg, rgba(96, 150, 240, 0.36), transparent);
}

.security-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.security-row span {
  display: grid;
  place-items: center;
  gap: 10px;
  color: rgba(224, 236, 255, 0.84);
  font-size: 14px;
  text-align: center;
}

.security-row svg {
  width: 26px;
  height: 26px;
  color: var(--blue-light);
  filter: drop-shadow(0 0 10px rgba(47, 123, 255, 0.45));
}

/* ---------- 市场公告卡片 ---------- */
.notice-card {
  position: absolute;
  top: 760px;
  right: 30px;
  width: 560px;
  box-sizing: border-box;
  padding: 22px 28px;
  z-index: 4;
}

.notice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.notice-head h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.notice-head a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--muted);
  font-size: 14px;
  text-decoration: none;
}

.notice-head a svg {
  width: 16px;
  height: 16px;
}

.notice-head a:hover {
  color: var(--cyan);
}

.notice-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.notice-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(96, 150, 240, 0.12);
}

.notice-list li:last-child {
  border-bottom: 0;
}

.notice-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--blue-light);
  box-shadow: 0 0 8px rgba(77, 155, 255, 0.8);
}

.notice-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: rgba(224, 236, 255, 0.86);
  font-size: 15px;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition: color 0.2s ease;
}

.notice-list li:hover .notice-title {
  color: var(--cyan);
  cursor: pointer;
}

.notice-date {
  flex-shrink: 0;
  color: var(--faint);
  font-size: 14px;
}

/* ---------- 页脚 ---------- */
.login-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 30px;
  display: grid;
  place-items: center;
  gap: 10px;
  color: rgba(224, 236, 255, 0.72);
  text-align: center;
}

.login-footer div {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 20px;
  letter-spacing: 4px;
}

.login-footer i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(77, 155, 255, 0.7);
  box-shadow: 0 0 10px rgba(77, 155, 255, 0.8);
}

.login-footer p {
  margin: 0;
  color: rgba(206, 224, 250, 0.56);
  font-size: 15px;
}

.login-footer a {
  color: rgba(206, 224, 250, 0.68);
  text-decoration: none;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
  }
}
</style>
