<template>
  <section v-if="enabled" class="graphical-captcha" aria-labelledby="captcha-title">
    <header>
      <strong id="captcha-title">安全验证</strong>
      <button type="button" :disabled="busy || coolingDown" @click="loadChallenge">
        <RefreshCwIcon aria-hidden="true" />刷新
      </button>
    </header>

    <div v-if="status === 'loading'" class="captcha-loading" role="status">正在加载验证内容…</div>
    <div v-else-if="status === 'loadError'" class="captcha-error" role="alert">
      <span>{{ feedback }}</span>
      <button type="button" @click="loadChallenge">重新加载</button>
    </div>
    <div v-else-if="status === 'rateLimited'" class="captcha-error" role="status" aria-live="polite">
      操作过于频繁，请在 {{ retryRemaining }} 秒后重试
    </div>
    <div v-else-if="status === 'verified'" class="captcha-passed" role="status">
      <CircleCheckIcon aria-hidden="true" />
      <span>安全验证已通过</span>
      <button type="button" @click="loadChallenge">重新验证</button>
    </div>
    <div v-else-if="challenge?.type === 'character'" class="legacy-captcha">
      <label>
        <span class="sr-only">请输入验证码</span>
        <input v-model="legacyCode" maxlength="6" autocomplete="off" placeholder="请输入验证码" @input="onLegacyInput" />
      </label>
      <img :src="challenge.imageUrl" alt="验证码" @error="loadChallenge('image-failed')" />
    </div>
    <template v-else-if="challenge">
      <p ref="promptRef" class="captcha-prompt" tabindex="-1">{{ challenge.prompt }}</p>
      <div
        class="captcha-grid"
        role="group"
        :aria-describedby="feedbackId"
        :style="{ '--captcha-columns': challenge.columns }"
        @keydown="onGridKeydown"
      >
        <button
          v-for="(tile, index) in challenge.tiles"
          :key="tile.tileId"
          :ref="(element) => setTileRef(element, index)"
          type="button"
          class="captcha-tile"
          :class="{ 'is-selected': selected.has(tile.tileId), 'is-broken': broken.has(tile.tileId) }"
          :aria-label="`验证图片 ${index + 1}`"
          :aria-pressed="selected.has(tile.tileId)"
          :disabled="imagesPending || broken.size > 0 || busy"
          @click="toggle(tile.tileId)"
        >
          <img :src="tile.imageUrl" alt="" @load="onImageLoad" @error="onImageError(tile.tileId)" />
          <span v-if="selected.has(tile.tileId)" class="tile-check" aria-hidden="true">✓</span>
        </button>
      </div>
      <p :id="feedbackId" class="captcha-feedback" aria-live="polite">{{ feedback }}</p>
      <div class="captcha-actions">
        <button
          v-if="challenge.alternativeModes?.length"
          type="button"
          class="alternative-button"
          disabled
          aria-describedby="alternative-unavailable"
        >替代验证暂不可用</button>
        <span v-else></span>
        <button type="button" class="verify-button" :disabled="busy || imagesPending || broken.size > 0" @click="verify">
          {{ status === 'verifying' ? '验证中…' : '验证' }}
        </button>
      </div>
      <p v-if="challenge.alternativeModes?.length" id="alternative-unavailable" class="captcha-feedback">替代验证尚未接入，请使用图形验证或联系平台支持。</p>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CircleCheck as CircleCheckIcon, RefreshCw as RefreshCwIcon } from '@lucide/vue'
import { createCaptchaChallenge, verifyCaptchaChallenge } from '@/api/auth'

const props = defineProps({
  scene: { type: String, default: 'password_login' },
  accountRevision: { type: Number, default: 0 },
})
const emit = defineEmits(['verified', 'invalidated', 'enabled-change'])

const status = ref('loading')
const enabled = ref(true)
const challenge = ref(null)
const selected = ref(new Set())
const broken = ref(new Set())
const loadedImages = ref(0)
const legacyCode = ref('')
const feedback = ref('')
const requestVersion = ref(0)
const promptRef = ref(null)
const tileRefs = ref([])
const feedbackId = `captcha-feedback-${Math.random().toString(36).slice(2)}`
let expiryTimer
let retryTimer
let expiresAt = 0
let retryUntil = 0
let pendingChallenge = null
const retryRemaining = ref(0)

const busy = computed(() => status.value === 'loading' || status.value === 'verifying')
const coolingDown = computed(() => status.value === 'rateLimited')
const imagesPending = computed(() => loadedImages.value < (challenge.value?.tiles?.length || 0))

function unwrap(response) {
  return response?.data ?? response ?? {}
}

function invalidate(reason) {
  clearTimeout(expiryTimer)
  expiresAt = 0
  emit('invalidated', reason)
}

function requireVerification() {
  enabled.value = true
  emit('enabled-change', true)
}

function setChallenge(value, message = '') {
  challenge.value = value
  selected.value = new Set()
  broken.value = new Set()
  loadedImages.value = 0
  tileRefs.value = []
  feedback.value = message
  legacyCode.value = ''
  status.value = 'ready'
  clearTimeout(expiryTimer)
  expiresAt = Number(value.expiresIn) > 0 ? Date.now() + Number(value.expiresIn) * 1000 : 0
  if (expiresAt) expiryTimer = setTimeout(checkExpiry, Math.max(0, expiresAt - Date.now()))
  nextTick(() => promptRef.value?.focus())
}

function acceptChallenge(data, message = '') {
  if (data.captchaEnabled === false) {
    enabled.value = false
    emit('enabled-change', false)
    status.value = 'ready'
    return
  }
  if (['character', 'text'].includes(data.type) && data.uuid && (data.imageUrl || data.img)) {
    setChallenge({ ...data, type: 'character', imageUrl: data.imageUrl || `data:image/gif;base64,${data.img}` }, message)
    return
  }
  if (data.type !== 'image_selection' || !data.challengeId || !data.prompt || !data.tiles?.length) {
    throw new Error('invalid graphical captcha challenge')
  }
  setChallenge({ ...data, columns: Math.min(3, Math.max(2, Math.floor(Number(data.columns) || 3))) }, message)
}

function showLoadError(message) {
  invalidate('unavailable')
  requireVerification()
  challenge.value = null
  status.value = 'loadError'
  feedback.value = message
}

async function loadChallenge(reason = 'refresh', message = '') {
  // Account changes still invalidate in-flight work while a server cooldown is active.
  const version = ++requestVersion.value
  invalidate(reason)
  requireVerification()
  challenge.value = null
  if (coolingDown.value) {
    if (reason === 'account-changed') pendingChallenge = null
    updateRetry()
    return
  }
  status.value = 'loading'
  try {
    const data = unwrap(await createCaptchaChallenge({ scene: props.scene, preferredMode: 'image_selection' }))
    if (version !== requestVersion.value) return
    acceptChallenge(data, message)
  } catch (error) {
    if (version !== requestVersion.value) return
    handleFailure(error, false)
  }
}

function updateRetry() {
  retryRemaining.value = Math.max(0, Math.ceil((retryUntil - Date.now()) / 1000))
  if (retryRemaining.value) return
  clearInterval(retryTimer)
  const pending = pendingChallenge
  pendingChallenge = null
  status.value = 'loading'
  const remaining = pending?.expiresAt ? (pending.expiresAt - Date.now()) / 1000 : 0
  if (pending && (!pending.expiresAt || remaining > 0)) {
    const next = pending.expiresAt ? { ...pending.data, expiresIn: remaining } : pending.data
    try { acceptChallenge(next) } catch { showLoadError('验证内容加载失败，请重试') }
  } else {
    loadChallenge('rate-limit-ended')
  }
}

function handleFailure(error, canReplace = true) {
  const code = error?.response?.data?.code ?? error?.code
  const data = error?.response?.data?.data ?? error?.data ?? {}
  invalidate('verify-failed')
  requireVerification()
  if (code === 'CAPTCHA_RATE_LIMITED') {
    challenge.value = null
    const seconds = Number(data.retryAfter)
    if (!Number.isFinite(seconds) || seconds <= 0) {
      showLoadError('操作过于频繁，请稍后重新加载')
      return
    }
    pendingChallenge = data.nextChallenge ? {
      data: data.nextChallenge,
      expiresAt: Number(data.nextChallenge.expiresIn) > 0 ? Date.now() + Number(data.nextChallenge.expiresIn) * 1000 : 0,
    } : null
    retryUntil = Date.now() + seconds * 1000
    status.value = 'rateLimited'
    updateRetry()
    retryTimer = setInterval(updateRetry, 1000)
    return
  }
  const messages = {
    CAPTCHA_INCORRECT: '选择不正确，请重试',
    CAPTCHA_EXPIRED: '验证已过期，请重新选择',
    CAPTCHA_CONSUMED: '验证已使用，请重新选择',
  }
  const message = messages[code]
  if (message && canReplace) {
    if (data.nextChallenge) {
      try { acceptChallenge(data.nextChallenge, message) } catch { showLoadError('验证内容加载失败，请重试') }
    } else {
      loadChallenge('verify-failed', message)
    }
    return
  }
  showLoadError(code === 'CAPTCHA_UNAVAILABLE' ? '验证服务暂不可用，请稍后重试'
    : error?.message?.includes('timeout') ? '验证请求超时，请重新加载' : '验证内容加载失败，请重试')
}

function checkExpiry() {
  if (coolingDown.value) updateRetry()
  if (expiresAt && Date.now() >= expiresAt) {
    loadChallenge('expired')
    return false
  }
  return status.value === 'verified' || challenge.value?.type === 'character'
}

function onResume() {
  if (document.visibilityState !== 'hidden') checkExpiry()
}

function onLegacyInput() {
  if (expiresAt && Date.now() >= expiresAt) {
    loadChallenge('expired')
    return
  }
  emit('invalidated', 'legacy-code-changed')
  if (legacyCode.value.trim()) {
    emit('verified', { code: legacyCode.value.trim(), uuid: challenge.value.uuid, legacy: true, expiresAt: expiresAt || undefined })
  }
}

function toggle(tileId) {
  const next = new Set(selected.value)
  next.has(tileId) ? next.delete(tileId) : next.add(tileId)
  selected.value = next
  feedback.value = `已选择 ${next.size} 张图片`
}

function onImageLoad() {
  loadedImages.value += 1
}

function onImageError(tileId) {
  broken.value = new Set([...broken.value, tileId])
  feedback.value = '图片加载失败，请刷新验证内容'
}

async function verify() {
  if (busy.value || coolingDown.value || !challenge.value || imagesPending.value || broken.value.size) return
  if (expiresAt && Date.now() >= expiresAt) {
    loadChallenge('expired')
    return
  }
  if (!selected.value.size) {
    feedback.value = '请至少选择一张图片'
    return
  }
  const version = requestVersion.value
  status.value = 'verifying'
  try {
    const data = unwrap(await verifyCaptchaChallenge(challenge.value.challengeId, [...selected.value]))
    if (version !== requestVersion.value) return
    if (!data.verified || !data.captchaToken) {
      showLoadError('验证结果无效，请重新验证')
      return
    }
    if (!Number.isFinite(Number(data.expiresIn)) || Number(data.expiresIn) <= 0) {
      showLoadError('验证凭证有效期无效，请重新验证')
      return
    }
    status.value = 'verified'
    challenge.value = null
    feedback.value = '安全验证已通过'
    clearTimeout(expiryTimer)
    expiresAt = Date.now() + Number(data.expiresIn) * 1000
    expiryTimer = setTimeout(checkExpiry, Math.max(0, expiresAt - Date.now()))
    emit('verified', { captchaToken: data.captchaToken, expiresAt })
  } catch (error) {
    if (version !== requestVersion.value) return
    handleFailure(error)
  }
}

function setTileRef(element, index) {
  if (element) tileRefs.value[index] = element
}

function onGridKeydown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
  const current = tileRefs.value.indexOf(document.activeElement)
  if (current < 0) return
  event.preventDefault()
  const columns = challenge.value.columns
  const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -columns, ArrowDown: columns }[event.key]
  const target = Math.min(tileRefs.value.length - 1, Math.max(0, current + offset))
  tileRefs.value[target]?.focus()
}

watch(() => props.accountRevision, () => loadChallenge('account-changed'), { flush: 'sync' })
onMounted(() => {
  loadChallenge()
  window.addEventListener('focus', onResume)
  document.addEventListener('visibilitychange', onResume)
})
onBeforeUnmount(() => {
  requestVersion.value += 1
  clearTimeout(expiryTimer)
  clearInterval(retryTimer)
  window.removeEventListener('focus', onResume)
  document.removeEventListener('visibilitychange', onResume)
})
defineExpose({ reset: loadChallenge, checkExpiry })
</script>

<style scoped>
.graphical-captcha { padding: 14px; border: 1px solid rgba(96,150,240,.28); border-radius: 12px; background: rgba(6,16,38,.55); }
.graphical-captcha header, .captcha-actions, .captcha-passed, .captcha-error { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.graphical-captcha header button, .captcha-actions button, .captcha-passed button, .captcha-error button { min-height: 44px; min-width: 44px; border: 0; background: transparent; color: #4d9bff; cursor: pointer; }
.graphical-captcha header button { display: inline-flex; align-items: center; gap: 5px; }
.graphical-captcha header svg { width: 15px; }
.captcha-prompt { margin: 10px 0; color: #eaf3ff; font-size: 14px; outline: none; }
.captcha-grid { display: grid; grid-template-columns: repeat(var(--captcha-columns), minmax(0, 1fr)); gap: 6px; }
.captcha-tile { position: relative; min-width: 44px; min-height: 44px; aspect-ratio: 1; padding: 0; overflow: hidden; border: 2px solid transparent; border-radius: 7px; background: #0b1b38; cursor: pointer; }
.captcha-tile img { display: block; width: 100%; height: 100%; object-fit: cover; }
.captcha-tile.is-selected { border-color: #35d0ff; box-shadow: 0 0 0 2px rgba(53,208,255,.25); }
.captcha-tile.is-broken { border-color: #ff7684; }
.tile-check { position: absolute; top: 4px; right: 4px; display: grid; width: 21px; height: 21px; place-items: center; border-radius: 50%; background: #1677ff; color: white; font-weight: 800; }
.captcha-feedback, .captcha-loading, .captcha-error, .captcha-passed { margin: 9px 0 0; min-height: 20px; color: rgba(206,224,250,.78); font-size: 13px; }
.captcha-passed { justify-content: flex-start; color: #62ddb3; }
.captcha-passed button { margin-left: auto; }
.captcha-passed svg { width: 20px; }
.captcha-error { color: #ff96a2; }
.verify-button { padding: 0 18px !important; border-radius: 7px !important; background: #2f7bff !important; color: white !important; }
button:focus-visible { outline: 2px solid #35d0ff; outline-offset: 2px; }
button:disabled { cursor: not-allowed !important; opacity: .5; }
.legacy-captcha { display: grid; grid-template-columns: minmax(0,1fr) 122px; gap: 10px; margin-top: 10px; }
.legacy-captcha input { width: 100%; height: 48px; box-sizing: border-box; border: 1px solid rgba(96,150,240,.3); border-radius: 8px; background: rgba(6,16,38,.5); color: #eaf3ff; padding: 0 12px; }
.legacy-captcha img { width: 122px; height: 48px; border-radius: 8px; object-fit: cover; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
