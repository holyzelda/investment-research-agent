<template>
  <div class="login-stage">
    <div class="ambient ambient-one"></div>
    <div class="ambient ambient-two"></div>
    <main class="login-page">
      <header class="brand-bar">
        <img :src="loginLogoUrl" alt="eTrader" />
        <div><strong>eTrader 2.0</strong><span>玄策电力交易智慧决策平台</span></div>
      </header>

      <section class="hero" aria-label="平台介绍">
        <p class="hero-kicker"><SparklesIcon aria-hidden="true" /> 智慧能源 · 专业决策</p>
        <h1>洞察市场脉络<br /><em>驱动交易决策</em></h1>
        <p>融合市场数据、智能算法与专业研究，让每一次能源决策更清晰、更可靠。</p>
        <div class="hero-stats" aria-label="平台核心能力">
          <span><strong>全流程</strong>交易辅助</span>
          <span><strong>AI</strong>智能分析</span>
          <span><strong>多维度</strong>风险洞察</span>
        </div>
      </section>

      <section class="capability-card glass-card" aria-label="平台核心能力">
        <div class="capability-grid">
          <article v-for="capability in capabilities" :key="capability.title">
            <component :is="capability.icon" aria-hidden="true" />
            <div><strong>{{ capability.title }}</strong><p>{{ capability.desc }}</p></div>
          </article>
        </div>
      </section>

      <section class="login-card glass-card" aria-label="用户登录">
        <header class="login-heading">
          <span>安全登录</span>
          <h2>欢迎回来</h2>
          <p>{{ loginMode === 'sms' ? '使用中国大陆手机号验证码登录' : '使用平台账号密码登录' }}</p>
        </header>

        <div class="login-tabs" role="tablist" aria-label="登录方式">
          <button :class="{ active: loginMode === 'sms' }" type="button" role="tab" :aria-selected="loginMode === 'sms'" @click="switchMode('sms')">验证码登录</button>
          <button :class="{ active: loginMode === 'password' }" type="button" role="tab" :aria-selected="loginMode === 'password'" @click="switchMode('password')">账号密码登录</button>
        </div>

        <form class="login-form" @submit.prevent="onLogin">
          <template v-if="loginMode === 'sms'">
            <div class="field-group">
              <label for="mobile">手机号</label>
              <div class="input-shell" :class="{ invalid: errors.mobile }">
                <span class="country-code">+86</span>
                <input id="mobile" v-model="smsForm.mobile" type="tel" inputmode="numeric" autocomplete="tel-national" maxlength="11" placeholder="请输入 11 位手机号" @input="onMobileInput" @blur="validateMobile" />
              </div>
              <p v-if="errors.mobile" class="field-error" role="alert">{{ errors.mobile }}</p>
            </div>
            <div class="field-group">
              <label for="sms-code">验证码</label>
              <div class="input-shell" :class="{ invalid: errors.code }">
                <KeyRoundIcon aria-hidden="true" />
                <input ref="smsCodeInput" id="sms-code" v-model="smsForm.code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="请输入 6 位验证码" @input="onCodeInput" />
                <button class="send-code" type="button" :disabled="!isMobileValid || sendingCode || countdown > 0" @click="sendCode">
                  {{ sendCodeText }}
                </button>
              </div>
              <p v-if="errors.code" class="field-error" role="alert">{{ errors.code }}</p>
              <p v-else-if="smsHint" class="field-hint" role="status">{{ smsHint }}</p>
            </div>
          </template>

          <template v-else>
            <div class="field-group">
              <label for="username">账号</label>
              <div class="input-shell"><UserIcon aria-hidden="true" /><input id="username" v-model="form.username" type="text" autocomplete="username" placeholder="请输入账号" /></div>
            </div>
            <div class="field-group">
              <label for="password">密码</label>
              <div class="input-shell"><LockKeyholeIcon aria-hidden="true" /><input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码" /><button class="ghost-eye" type="button" aria-label="显示或隐藏密码" @click="showPassword = !showPassword"><component :is="showPassword ? EyeIcon : EyeOffIcon" aria-hidden="true" /></button></div>
            </div>
            <div v-if="captchaEnabled" class="captcha-row">
              <div class="input-shell"><ShieldCheckIcon aria-hidden="true" /><input v-model="form.code" type="text" autocomplete="off" maxlength="6" placeholder="图形验证码" /></div>
              <button class="captcha-image" :class="{ 'is-error': captchaError }" type="button" aria-label="刷新验证码" @click="getCode"><img v-if="codeUrl && !captchaError" :src="codeUrl" alt="验证码" @error="captchaError = true" /><span v-else><RefreshCwIcon aria-hidden="true" />刷新</span></button>
            </div>
          </template>

          <button class="login-submit" type="submit" :disabled="!canSubmit || loading">
            <LoaderCircleIcon v-if="loading" class="spin" aria-hidden="true" />
            {{ loading ? '登录中...' : '登录平台' }}
          </button>
        </form>

        <div class="login-divider"><span>安全连接 · 全程守护</span></div>
        <div class="security-row"><span><ShieldCheckIcon />统一身份认证</span><span><LockKeyholeIcon />数据安全加密</span></div>
      </section>

      <section class="quick-card glass-card" aria-label="快速入口"><div class="quick-grid"><span v-for="entry in quickEntries" :key="entry.title"><component :is="entry.icon" /><b>{{ entry.title }}</b></span></div></section>
      <footer class="login-footer">西安玄策电力交易辅助中心 版权所有 © 2026 · <a href="https://beian.miit.gov.cn/#/Integrated/recordQuery" target="_blank" rel="noopener noreferrer">陕ICP备20010223号-3</a></footer>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { BrainCircuit as BrainCircuitIcon, ChartNoAxesCombined as ChartIcon, Eye as EyeIcon, EyeOff as EyeOffIcon, FileQuestion as FileQuestionIcon, Headphones as HeadphonesIcon, KeyRound as KeyRoundIcon, LoaderCircle as LoaderCircleIcon, LockKeyhole as LockKeyholeIcon, RefreshCw as RefreshCwIcon, ShieldCheck as ShieldCheckIcon, Sparkles as SparklesIcon, User as UserIcon } from '@lucide/vue'
import { useSessionStore } from '@/store/modules/session'
import { usePermissionStore } from '@/store/modules/permission'
import { getCodeImg, sendSmsCode } from '@/api/auth'
import { clearLoginRequired } from '@/utils/auth'
import loginLogoUrl from '@/assets/images/eTrader_logo2.png'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()
const permission = usePermissionStore()
const loginMode = ref('sms')
const loading = ref(false)
const sendingCode = ref(false)
const showPassword = ref(false)
const codeUrl = ref('')
const captchaEnabled = ref(true)
const captchaError = ref(false)
const countdown = ref(0)
const smsHint = ref('')
const smsCodeInput = ref(null)
const codeSentTo = ref('')
let countdownTimer
const form = reactive({ username: '', password: '', code: '', uuid: '' })
const smsForm = reactive({ mobile: '', code: '', requestId: '' })
const errors = reactive({ mobile: '', code: '' })
const capabilities = [
  { icon: ChartIcon, title: '全流程交易辅助', desc: '覆盖交易关键环节' },
  { icon: BrainCircuitIcon, title: 'AI 智能决策引擎', desc: '融合数据与先进算法' },
]
const quickEntries = [{ icon: FileQuestionIcon, title: '帮助中心' }, { icon: HeadphonesIcon, title: '联系我们' }]
const isMobileValid = computed(() => /^1\d{10}$/.test(smsForm.mobile))
const canSubmit = computed(() => loginMode.value === 'sms' ? isMobileValid.value && /^\d{6}$/.test(smsForm.code) : Boolean(form.username.trim() && form.password && (!captchaEnabled.value || form.code)))
const sendCodeText = computed(() => sendingCode.value ? '发送中...' : countdown.value > 0 ? `${countdown.value}s 后重发` : smsForm.requestId ? '重新获取' : '获取验证码')

function switchMode(mode) {
  loginMode.value = mode
  errors.mobile = ''
  errors.code = ''
  if (mode === 'password' && !codeUrl.value) getCode()
}
function normalizeMobile(value) {
  const digits = String(value || '').replace(/\D/g, '')
  return (digits.startsWith('86') && digits.length > 11 ? digits.slice(2) : digits).slice(0, 11)
}
function onMobileInput(event) {
  const nextMobile = normalizeMobile(event.target.value)
  smsForm.mobile = nextMobile
  if (codeSentTo.value && nextMobile !== codeSentTo.value) {
    smsForm.code = ''
    smsForm.requestId = ''
    smsHint.value = ''
    codeSentTo.value = ''
  }
  errors.mobile = ''
}
function onCodeInput(event) {
  smsForm.code = event.target.value.replace(/\D/g, '').slice(0, 6)
  errors.code = ''
}
function validateMobile() {
  errors.mobile = smsForm.mobile && !isMobileValid.value ? '请输入正确的中国大陆手机号' : ''
  return !errors.mobile
}
function maskMobile(mobile) { return `${mobile.slice(0, 3)}****${mobile.slice(-4)}` }
function startCountdown(seconds) {
  window.clearInterval(countdownTimer)
  countdown.value = Math.max(1, Number(seconds) || 60)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(countdownTimer)
  }, 1000)
}
async function sendCode() {
  if (!validateMobile() || !isMobileValid.value || sendingCode.value || countdown.value > 0) return
  sendingCode.value = true
  errors.code = ''
  try {
    const res = await sendSmsCode(smsForm.mobile)
    const data = res?.data || {}
    smsForm.requestId = data.requestId || data.request_id || data.uuid || ''
    codeSentTo.value = smsForm.mobile
    startCountdown(data.retryAfter || data.retry_after || 60)
    smsHint.value = `验证码已发送至 ${maskMobile(smsForm.mobile)}`
    await nextTick()
    smsCodeInput.value?.focus()
  } catch (error) {
    errors.code = error.message || '验证码发送失败，请稍后重试'
  } finally { sendingCode.value = false }
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
function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/home'
}
async function onLogin() {
  if (!canSubmit.value) {
    if (loginMode.value === 'sms') {
      validateMobile()
      if (!/^\d{6}$/.test(smsForm.code)) errors.code = '请输入 6 位数字验证码'
    }
    return
  }
  loading.value = true
  try {
    if (loginMode.value === 'sms') await session.loginBySms(smsForm)
    else await session.login(form)
    clearLoginRequired()
    permission.resetRoutes()
    try { await session.loadUserInfo({ force: true }) } catch (infoError) { console.warn('[login] 用户信息加载失败：', infoError) }
    router.push(safeRedirect(route.query.redirect))
  } catch (error) {
    if (loginMode.value === 'sms') errors.code = error.message || '验证码错误或已失效，请重新输入或获取'
    else { ElMessage.error(error.message || '登录失败'); getCode() }
  } finally { loading.value = false }
}
onBeforeUnmount(() => window.clearInterval(countdownTimer))
</script>

<style scoped>
:global(body) { margin: 0; background: #06101f; }
* { box-sizing: border-box; }
.login-stage { position: fixed; inset: 0; overflow: auto; color: #eef6ff; background: radial-gradient(circle at 18% 18%, rgba(35, 103, 157, .33), transparent 31%), radial-gradient(circle at 76% 88%, rgba(12, 111, 118, .22), transparent 32%), linear-gradient(135deg, #071526 0%, #07111f 46%, #040b15 100%); font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif; }
.login-stage::before { position: fixed; inset: 0; content: ""; opacity: .16; background-image: linear-gradient(rgba(111, 175, 218, .22) 1px, transparent 1px), linear-gradient(90deg, rgba(111, 175, 218, .22) 1px, transparent 1px); background-size: 56px 56px; mask-image: linear-gradient(to bottom, #000, transparent 82%); }
.ambient { position: fixed; border-radius: 50%; filter: blur(2px); pointer-events: none; }
.ambient-one { width: 420px; height: 420px; left: 10%; top: 20%; border: 1px solid rgba(67, 193, 221, .12); box-shadow: 0 0 100px rgba(38, 157, 190, .08), inset 0 0 80px rgba(38, 157, 190, .06); }
.ambient-two { width: 600px; height: 600px; right: -260px; bottom: -250px; border: 1px solid rgba(74, 127, 204, .14); }
.login-page { position: relative; z-index: 1; width: min(1180px, calc(100% - 64px)); min-height: 100vh; margin: auto; padding: 38px 0 34px; display: grid; grid-template-columns: minmax(0, 1fr) 420px; grid-template-rows: auto 1fr auto; column-gap: 110px; }
.brand-bar { grid-column: 1 / -1; display: flex; align-items: center; gap: 13px; }
.brand-bar img { width: 50px; height: 50px; object-fit: contain; filter: drop-shadow(0 0 14px rgba(70, 154, 230, .5)); }
.brand-bar strong, .brand-bar span { display: block; }.brand-bar strong { font-size: 20px; }.brand-bar span { margin-top: 4px; color: #8fa9c3; font-size: 13px; }
.hero { align-self: center; padding-bottom: 80px; }.hero-kicker { display: flex; align-items: center; gap: 8px; color: #57d0de !important; font-size: 14px !important; letter-spacing: 2px; }.hero-kicker svg { width: 18px; }.hero h1 { margin: 22px 0; font-size: clamp(42px, 4vw, 62px); line-height: 1.22; letter-spacing: 2px; }.hero h1 em { color: #6ed4df; font-style: normal; }.hero > p { max-width: 620px; color: #9db2c8; font-size: 17px; line-height: 1.9; }
.hero-stats { display: flex; gap: 38px; margin-top: 42px; color: #7894ad; font-size: 13px; }.hero-stats span { padding-left: 15px; border-left: 2px solid rgba(83, 201, 214, .42); }.hero-stats strong { display: block; margin-bottom: 5px; color: #ddebfa; font-size: 19px; }
.glass-card { border: 1px solid rgba(136, 183, 218, .16); border-radius: 22px; background: linear-gradient(145deg, rgba(14, 35, 59, .84), rgba(8, 23, 42, .72)); box-shadow: 0 28px 80px rgba(0, 5, 14, .46); backdrop-filter: blur(18px); }
.login-card { align-self: center; padding: 34px 36px 30px; }.login-heading > span { color: #5ed0dc; font-size: 12px; letter-spacing: 3px; }.login-heading h2 { margin: 8px 0 7px; font-size: 29px; }.login-heading p { margin: 0; color: #819ab3; font-size: 14px; }
.login-tabs { display: grid; grid-template-columns: 1fr 1fr; margin: 26px 0 24px; border-bottom: 1px solid rgba(132, 174, 207, .14); }.login-tabs button { position: relative; padding: 0 0 13px; border: 0; background: none; color: #718ca6; font-size: 14px; cursor: pointer; }.login-tabs button.active { color: #e8f4ff; }.login-tabs button.active::after { position: absolute; left: 23%; right: 23%; bottom: -1px; height: 2px; content: ""; background: #55ccd9; box-shadow: 0 0 10px rgba(85, 204, 217, .6); }
.login-form { display: grid; gap: 17px; }.field-group > label { display: block; margin-bottom: 8px; color: #abc0d3; font-size: 13px; }.input-shell { position: relative; display: flex; align-items: center; min-height: 50px; border: 1px solid rgba(125, 166, 198, .2); border-radius: 10px; background: rgba(3, 14, 28, .52); transition: border-color .2s, box-shadow .2s; }.input-shell:focus-within { border-color: rgba(87, 208, 222, .65); box-shadow: 0 0 0 3px rgba(71, 183, 198, .1); }.input-shell.invalid { border-color: rgba(241, 103, 111, .68); }.input-shell > svg { width: 18px; margin-left: 15px; color: #6686a2; }.input-shell input { min-width: 0; flex: 1; height: 48px; padding: 0 14px; border: 0; outline: 0; background: transparent; color: #edf7ff; font-size: 15px; }.input-shell input::placeholder { color: #506b84; }.country-code { height: 24px; padding: 3px 14px; border-right: 1px solid rgba(137, 174, 204, .22); color: #d2e3f0; font-size: 14px; }.send-code { flex: 0 0 auto; margin-right: 5px; padding: 10px 11px; border: 0; border-left: 1px solid rgba(130, 174, 207, .16); background: transparent; color: #55ccd9; cursor: pointer; }.send-code:disabled { color: #506b82; cursor: not-allowed; }.field-error, .field-hint { margin: 6px 2px 0; font-size: 12px; }.field-error { color: #ff8990; }.field-hint { color: #69bfbd; }
.ghost-eye { display: grid; width: 44px; border: 0; background: none; color: #718ba3; place-items: center; cursor: pointer; }.ghost-eye svg { width: 18px; }.captcha-row { display: grid; grid-template-columns: 1fr 108px; gap: 10px; }.captcha-image { border: 1px solid rgba(125, 166, 198, .2); border-radius: 10px; overflow: hidden; background: rgba(3, 14, 28, .52); color: #8da7bd; }.captcha-image img { width: 100%; height: 48px; object-fit: cover; }.captcha-image span { display: flex; align-items: center; justify-content: center; gap: 5px; }.captcha-image svg { width: 15px; }
.login-submit { display: flex; align-items: center; justify-content: center; gap: 8px; height: 52px; margin-top: 5px; border: 0; border-radius: 10px; background: linear-gradient(100deg, #26839e, #316aa4); box-shadow: 0 12px 26px rgba(19, 95, 132, .3); color: white; font-size: 16px; font-weight: 600; letter-spacing: 2px; cursor: pointer; }.login-submit:disabled { opacity: .46; cursor: not-allowed; }.spin { width: 18px; animation: spin 1s linear infinite; }
.login-divider { display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: center; margin: 24px 0 18px; color: #58728a; font-size: 11px; }.login-divider::before, .login-divider::after { height: 1px; content: ""; background: rgba(129, 169, 199, .14); }.security-row { display: flex; justify-content: center; gap: 26px; color: #68849d; font-size: 11px; }.security-row span { display: flex; align-items: center; gap: 5px; }.security-row svg { width: 14px; }
.capability-card { position: absolute; left: 0; bottom: 95px; padding: 18px 22px; border-radius: 16px; box-shadow: none; }.capability-grid { display: flex; gap: 28px; }.capability-grid article { display: flex; align-items: center; gap: 11px; min-width: 190px; }.capability-grid svg { width: 25px; color: #4fc5d4; }.capability-grid strong { font-size: 13px; }.capability-grid p { margin: 4px 0 0; color: #6d879f; font-size: 11px; }
.quick-card { display: none; }.quick-grid { display: flex; }.login-footer { grid-column: 1 / -1; align-self: end; color: #526b82; font-size: 12px; text-align: center; }.login-footer a { color: #637e96; text-decoration: none; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 820px) {
  .login-stage { position: absolute; min-height: 100%; }.login-page { width: min(100% - 40px, 480px); min-height: 100dvh; padding: 24px 0; display: flex; flex-direction: column; }.brand-bar img { width: 42px; height: 42px; }.brand-bar strong { font-size: 17px; }.brand-bar span { font-size: 11px; }.hero { padding: 48px 3px 28px; }.hero-kicker, .hero > p, .hero-stats { display: none; }.hero h1 { margin: 0; font-size: 30px; line-height: 1.35; }.login-card { width: 100%; padding: 28px 22px 25px; }.capability-card, .quick-card { display: none; }.login-footer { margin-top: 28px; line-height: 1.7; }.security-row { gap: 15px; }
}
@media (max-width: 390px) { .login-page { width: calc(100% - 28px); }.login-card { padding-inline: 17px; }.send-code { padding-inline: 7px; font-size: 12px; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
