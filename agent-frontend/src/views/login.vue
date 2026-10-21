<template>
  <div class="login-stage" :style="{ '--login-bg-image': `url(${loginBackgroundUrl})` }">
    <main class="login-page">
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
      <p class="hero-sub">让稳定的<em>清洁电力</em>惠及每一个人</p>
    </section>

    <section class="capability-card glass-card" aria-label="平台核心能力">

      <div class="capability-grid">
        <article v-for="capability in capabilities" :key="capability.title" class="capability-item">
          <span class="capability-icon">
            <component :is="capability.icon" aria-hidden="true" />
          </span>
          <strong>{{ capability.title }}</strong>
          <p>{{ capability.desc }}</p>
        </article>
      </div>
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
        <GraphicalCaptcha
          ref="captchaRef"
          @verified="onCaptchaVerified"
          @invalidated="onCaptchaInvalidated"
          @enabled-change="captchaEnabled = $event"
        />

        <div class="form-tools">
          <a href="javascript:void(0)">忘记密码?</a>
        </div>

        <button class="login-submit" type="submit" :disabled="!canLogin">
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

    <section class="quick-card glass-card" aria-label="快速入口">
      <header class="quick-head">
        <h3>快速入口</h3>
        <ChevronRightIcon aria-hidden="true" />
      </header>
      <div class="quick-grid">
        <a
          v-for="entry in quickEntries"
          :key="entry.title"
          :class="`is-${entry.tone}`"
          href="javascript:void(0)"
          class="quick-entry"
        >
          <span class="quick-icon">
            <component :is="entry.icon" aria-hidden="true" />
          </span>
          <strong>{{ entry.title }}</strong>
          <span>{{ entry.desc }}</span>
        </a>
      </div>
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
        西安玄策电力交易辅助中心 版权所有 © 2026
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  BookOpen as BookOpenIcon,
  Boxes as BoxesIcon,
  BrainCircuit as BrainCircuitIcon,
  ChevronDown as ChevronDownIcon,
  ChevronRight as ChevronRightIcon,
  CircleHelp as CircleHelpIcon,
  ContactRound as ContactRoundIcon,
  Eye as EyeIcon,
  EyeOff as EyeOffIcon,
  Headphones as HeadphonesIcon,
  KeyRound as KeyRoundIcon,
  LockKeyhole as LockKeyholeIcon,
  Megaphone as MegaphoneIcon,
  Network as NetworkIcon,
  Route as RouteIcon,
  Settings2 as Settings2Icon,
  ShieldCheck as ShieldCheckIcon,
  User as UserIcon,
  UserRound as UserRoundIcon,
} from '@lucide/vue'
import { useSessionStore } from '@/store/modules/session'
import { usePermissionStore } from '@/store/modules/permission'
import GraphicalCaptcha from '@/components/GraphicalCaptcha.vue'
import { clearLoginRequired } from '@/utils/auth'
import loginBackgroundUrl from '@/assets/images/login_bg.png'
import loginLogoUrl from '@/assets/images/eTrader_logo2.png'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()
const permission = usePermissionStore()
const loading = ref(false)
const showPassword = ref(false)
const captchaEnabled = ref(true)
const captchaVerified = ref(false)
const captchaRef = ref(null)
const captchaExpiresAt = ref(0)
const form = reactive({ username: '', password: '', captchaToken: '', code: undefined, uuid: undefined })
const canLogin = computed(() => Boolean(
  form.username.trim() && form.password && (!captchaEnabled.value || (captchaVerified.value && (!captchaExpiresAt.value || Date.now() < captchaExpiresAt.value))) && !loading.value,
))

const capabilities = [
  {
    icon: BoxesIcon,
    title: '全流程交易辅助',
    desc: '覆盖交易全流程，提供专业工具与自动化支持，提升交易效率与决策能力。',
  },
  {
    icon: BrainCircuitIcon,
    title: 'AI 智能决策引擎',
    desc: '融合多源数据与先进算法，驱动策略生成与优化，辅助科学决策。',
  },
  {
    icon: ShieldCheckIcon,
    title: '风险控制体系',
    desc: '多维度风险识别与预警，构建稳健风控体系，保障交易安全。',
  },
  {
    icon: NetworkIcon,
    title: '数据洞察',
    desc: '汇聚交易与市场数据，提供多维分析与趋势洞察，让关键变化清晰可见。',
  },
]

const quickEntries = [
  { icon: RouteIcon, title: '新手引导', desc: '快速了解平台\n功能与操作', tone: 'purple' },
  { icon: BookOpenIcon, title: '产品文档', desc: '查看平台使用\n手册与说明', tone: 'green' },
  { icon: CircleHelpIcon, title: '常见问题', desc: '解答使用过程中\n常见问题', tone: 'amber' },
  { icon: ContactRoundIcon, title: '联系我们', desc: '获取专业团队\n支持与服务', tone: 'cyan' },
]

const authMethods = [
  { icon: ShieldCheckIcon, label: '统一身份认证' },
  { icon: KeyRoundIcon, label: '安全会话' },
  { icon: Settings2Icon, label: '权限动态管控' },
]

function onCaptchaVerified({ captchaToken, code, uuid, expiresAt }) {
  captchaExpiresAt.value = expiresAt || 0
  form.captchaToken = captchaToken || ''
  form.code = code
  form.uuid = uuid
  captchaVerified.value = true
}

function onCaptchaInvalidated() {
  captchaExpiresAt.value = 0
  form.captchaToken = ''
  form.code = undefined
  form.uuid = undefined
  captchaVerified.value = false
}

function checkCaptchaExpiry() {
  if (captchaExpiresAt.value && Date.now() >= captchaExpiresAt.value) {
    onCaptchaInvalidated()
    captchaRef.value?.reset('token-expired')
  }
}

function onResume() {
  if (document.visibilityState !== 'hidden') checkCaptchaExpiry()
}

async function onLogin() {
  if (loading.value) return
  checkCaptchaExpiry()
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  if (captchaEnabled.value && !captchaVerified.value) {
    ElMessage.warning('请先完成安全验证')
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
    form.password = ''
    captchaRef.value?.reset('login-failed')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  window.addEventListener('focus', onResume)
  document.addEventListener('visibilitychange', onResume)
})

watch(() => form.username, () => {
  onCaptchaInvalidated()
  captchaEnabled.value = true
  captchaRef.value?.reset('account-changed')
}, { flush: 'sync' })

onBeforeUnmount(() => {
  window.removeEventListener('focus', onResume)
  document.removeEventListener('visibilitychange', onResume)
})
</script>

<style scoped>
:global(body) {
  margin: 0;
  background: #050b1a;
}

.login-stage {
  min-height: 100dvh;
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
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 28px;
  box-sizing: border-box;
  color: var(--text);
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}

.login-canvas {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 440px);
  grid-template-areas: "brand nav" "hero login" "capabilities login" "quick quick" "footer footer";
  gap: 32px;
  align-items: start;
}

/* ---------- 品牌 ---------- */
.brand-bar {
  grid-area: brand;
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
  grid-area: nav;
  justify-content: flex-end;
  flex-wrap: wrap;
  display: flex;
  align-items: center;
  gap: 12px;
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
  padding-right: 12px;
  min-height: 44px;
  border-right: 1px solid rgba(255, 255, 255, 0.16);
}

.top-nav a:hover,
.lang-btn:hover {
  color: var(--cyan);
}

.top-nav svg,
.login-card > header svg,
.security-row svg {
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
  grid-area: hero;
  padding-top: 28px;
}

.hero-title {
  margin: 0;
  font-size: clamp(30px, 3.5vw, 50px);
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

/* ---------- 玻璃卡片通用 ---------- */
.glass-card {
  border-radius: 16px;
  background: var(--panel-bg);
  backdrop-filter: blur(4px);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

/* ---------- 平台核心能力 ---------- */
.capability-card {
  grid-area: capabilities;
  box-sizing: border-box;
  padding: 22px 26px 28px;
  z-index: 4;
}

.capability-card h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 28px;
  margin-top: 28px;
}

.capability-item {
  display: flex;
  flex-direction: column;
}

.capability-icon {
  display: grid;
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  place-items: center;
  color: var(--cyan);
  background: linear-gradient(160deg, rgba(53, 208, 255, 0.24), rgba(47, 123, 255, 0.14));
  border: 1px solid rgba(77, 155, 255, 0.42);
  clip-path: polygon(50% 0, 100% 22%, 100% 78%, 50% 100%, 0 78%, 0 22%);
}

.capability-icon svg {
  width: 29px;
  height: 29px;
  stroke-width: 1.8;
  filter: drop-shadow(0 0 10px rgba(53, 208, 255, 0.5));
}

.capability-item strong {
  color: rgba(237, 245, 255, 0.96);
  font-size: 17px;
  font-weight: 700;
  text-align: center;
}

.capability-item p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

/* ---------- 登录卡片 ---------- */
.login-card {
  grid-area: login;
  min-width: 0;
  box-sizing: border-box;
  padding: 24px;
  border-radius: 20px;
  z-index: 4;
}

.login-card > header {
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
  width: 44px;
  height: 44px;
  border: 0;
  background: transparent;
  color: rgba(206, 224, 250, 0.72);
  cursor: pointer;
}

.ghost-eye svg {
  width: 20px;
  height: 20px;
}

.form-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.form-tools a {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
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

/* ---------- 快速入口 ---------- */
.quick-card {
  grid-area: quick;
  box-sizing: border-box;
  padding: 22px 28px 26px;
  z-index: 4;
}

.quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quick-head h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.quick-head svg {
  width: 16px;
  height: 16px;
  color: var(--muted);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 26px;
}

.quick-entry {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  color: inherit;
  text-align: center;
  text-decoration: none;
}

.quick-icon {
  display: grid;
  width: 54px;
  height: 54px;
  margin-bottom: 14px;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 10px;
  background: color-mix(in srgb, currentColor 18%, transparent);
  box-shadow: 0 0 18px color-mix(in srgb, currentColor 24%, transparent);
}

.quick-icon svg {
  width: 28px;
  height: 28px;
  stroke-width: 1.8;
}

.quick-entry strong {
  color: rgba(237, 245, 255, 0.96);
  font-size: 16px;
  font-weight: 700;
}

.quick-entry > span:last-child {
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-line;
}

.quick-entry:hover strong {
  color: var(--cyan);
}

.quick-entry.is-purple {
  color: #8d5cff;
}

.quick-entry.is-green {
  color: #1ecf9a;
}

.quick-entry.is-amber {
  color: #f0ae3d;
}

.quick-entry.is-cyan {
  color: #39b9ff;
}

/* ---------- 页脚 ---------- */
.login-footer {
  grid-area: footer;
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

@media (max-width: 900px) {
  .login-page { padding: 20px 16px; }
  .login-canvas {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: "brand" "hero" "login" "capabilities" "quick" "footer";
    gap: 24px;
  }
  .top-nav { display: none; }
  .brand-text strong { font-size: 20px; }
  .brand-text span { font-size: 13px; }
  .hero { padding-top: 0; }
  .hero-sub { font-size: 18px; margin-top: 14px; }
  .login-card { width: 100%; max-width: 480px; justify-self: center; padding: 20px 16px; }
  .capability-card, .quick-card { padding: 20px 16px; }
  .capability-grid, .quick-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px 16px; }
  .login-footer p { font-size: 12px; line-height: 1.8; }
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
