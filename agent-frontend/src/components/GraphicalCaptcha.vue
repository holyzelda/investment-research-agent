<template>
  <section v-if="enabled" class="graphical-captcha" aria-labelledby="captcha-title">
    <header>
      <strong id="captcha-title">安全验证</strong>
      <button type="button" :disabled="busy" @click="loadChallenge">
        <RefreshCwIcon aria-hidden="true" />刷新
      </button>
    </header>

    <div v-if="status === 'loading'" class="captcha-loading" role="status">正在加载验证内容…</div>
    <div v-else-if="status === 'loadError'" class="captcha-error" role="alert">
      <span>验证内容加载失败，请重试</span>
      <button type="button" @click="loadChallenge">重新加载</button>
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
          @click="loadAlternative"
        >换一个验证方式</button>
        <span v-else></span>
        <button type="button" class="verify-button" :disabled="busy || imagesPending || broken.size > 0" @click="verify">
          {{ status === 'verifying' ? '验证中…' : '验证' }}
        </button>
      </div>
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

const busy = computed(() => status.value === 'loading' || status.value === 'verifying')
const imagesPending = computed(() => loadedImages.value < (challenge.value?.tiles?.length || 0))

function unwrap(response) {
  return response?.data ?? response ?? {}
}

function invalidate(reason) {
  clearTimeout(expiryTimer)
  emit('invalidated', reason)
}

function setChallenge(value) {
  challenge.value = value
  selected.value = new Set()
  broken.value = new Set()
  loadedImages.value = 0
  feedback.value = ''
  legacyCode.value = ''
  status.value = 'ready'
  clearTimeout(expiryTimer)
  if (value.expiresIn) expiryTimer = setTimeout(() => loadChallenge('expired'), value.expiresIn * 1000)
  nextTick(() => promptRef.value?.focus())
}

async function loadChallenge(reason = 'refresh', preferredMode = 'image_selection') {
  const version = ++requestVersion.value
  invalidate(reason)
  challenge.value = null
  status.value = 'loading'
  try {
    const data = unwrap(await createCaptchaChallenge({ scene: props.scene, preferredMode }))
    if (version !== requestVersion.value) return
    enabled.value = data.captchaEnabled !== false
    emit('enabled-change', enabled.value)
    if (!enabled.value) {
      status.value = 'ready'
      return
    }
    if (['character', 'text'].includes(data.type) && data.uuid && (data.imageUrl || data.img)) {
      setChallenge({ type: 'character', uuid: data.uuid, imageUrl: data.imageUrl || `data:image/gif;base64,${data.img}` })
      return
    }
    if (data.type !== 'image_selection' || !data.challengeId || !data.prompt || !data.tiles?.length) {
      throw new Error('invalid graphical captcha challenge')
    }
    setChallenge({ ...data, columns: Math.min(3, Math.max(2, Number(data.columns) || 3)) })
  } catch {
    if (version !== requestVersion.value) return
    status.value = 'loadError'
    feedback.value = '验证内容加载失败，请重试'
  }
}

function loadAlternative() {
  loadChallenge('alternative', challenge.value.alternativeModes[0])
}

function onLegacyInput() {
  invalidate('legacy-code-changed')
  if (legacyCode.value.trim()) {
    emit('verified', { code: legacyCode.value.trim(), uuid: challenge.value.uuid, legacy: true })
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
  if (!selected.value.size) {
    feedback.value = '请至少选择一张图片'
    return
  }
  const version = requestVersion.value
  status.value = 'verifying'
  try {
    const data = unwrap(await verifyCaptchaChallenge(challenge.value.challengeId, [...selected.value]))
    if (version !== requestVersion.value) return
    if (!data.verified || !data.captchaToken) throw new Error('CAPTCHA_INCORRECT')
    status.value = 'verified'
    challenge.value = null
    feedback.value = '安全验证已通过'
    clearTimeout(expiryTimer)
    const expiresAt = Date.now() + (Number(data.expiresIn) || 120) * 1000
    expiryTimer = setTimeout(() => loadChallenge('token-expired'), Math.max(0, expiresAt - Date.now()))
    emit('verified', { captchaToken: data.captchaToken, expiresAt })
  } catch (error) {
    if (version !== requestVersion.value) return
    feedback.value = error?.message?.includes('timeout') ? '验证请求超时，请重试' : '选择不正确，请重试'
    await loadChallenge('verify-failed')
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

watch(() => props.accountRevision, () => loadChallenge('account-changed'))
onMounted(loadChallenge)
onBeforeUnmount(() => {
  requestVersion.value += 1
  clearTimeout(expiryTimer)
})
defineExpose({ reset: loadChallenge })
</script>

<style scoped>
.graphical-captcha { padding: 14px; border: 1px solid rgba(96,150,240,.28); border-radius: 12px; background: rgba(6,16,38,.55); }
.graphical-captcha header, .captcha-actions, .captcha-passed, .captcha-error { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.graphical-captcha header button, .captcha-actions button, .captcha-passed button, .captcha-error button { min-height: 32px; border: 0; background: transparent; color: #4d9bff; cursor: pointer; }
.graphical-captcha header button { display: inline-flex; align-items: center; gap: 5px; }
.graphical-captcha header svg { width: 15px; }
.captcha-prompt { margin: 10px 0; color: #eaf3ff; font-size: 14px; outline: none; }
.captcha-grid { display: grid; grid-template-columns: repeat(var(--captcha-columns), minmax(0, 1fr)); gap: 6px; }
.captcha-tile { position: relative; min-width: 44px; aspect-ratio: 1; padding: 0; overflow: hidden; border: 2px solid transparent; border-radius: 7px; background: #0b1b38; cursor: pointer; }
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
button:disabled { cursor: not-allowed !important; opacity: .5; }
.legacy-captcha { display: grid; grid-template-columns: minmax(0,1fr) 122px; gap: 10px; margin-top: 10px; }
.legacy-captcha input { width: 100%; height: 48px; box-sizing: border-box; border: 1px solid rgba(96,150,240,.3); border-radius: 8px; background: rgba(6,16,38,.5); color: #eaf3ff; padding: 0 12px; }
.legacy-captcha img { width: 122px; height: 48px; border-radius: 8px; object-fit: cover; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
