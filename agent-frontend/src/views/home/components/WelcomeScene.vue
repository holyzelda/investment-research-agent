<template>
  <div class="ir-welcome-scene" aria-hidden="true">
    <svg
      class="ir-welcome-scene__svg"
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <radialGradient id="ir-scene-atmosphere" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="var(--scene-atmosphere-core)" />
          <stop offset="58%" stop-color="var(--scene-atmosphere-mid)" />
          <stop offset="100%" stop-color="var(--scene-transparent)" />
        </radialGradient>
        <radialGradient id="ir-scene-core-field" cx="50%" cy="44%" r="58%">
          <stop offset="0%" stop-color="var(--scene-core-center)" />
          <stop offset="72%" stop-color="var(--scene-core-edge)" />
          <stop offset="100%" stop-color="var(--scene-transparent)" />
        </radialGradient>
        <linearGradient id="ir-scene-metal-front" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--scene-metal-front-hi)" />
          <stop offset="100%" stop-color="var(--scene-metal-front-lo)" />
        </linearGradient>
        <linearGradient id="ir-scene-metal-side" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--scene-metal-side-hi)" />
          <stop offset="100%" stop-color="var(--scene-metal-side-lo)" />
        </linearGradient>
        <linearGradient id="ir-scene-metal-top" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stop-color="var(--scene-metal-top-lo)" />
          <stop offset="100%" stop-color="var(--scene-metal-top-hi)" />
        </linearGradient>
        <linearGradient id="ir-scene-panel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--scene-panel-hi)" />
          <stop offset="100%" stop-color="var(--scene-panel-lo)" />
        </linearGradient>
        <linearGradient id="ir-scene-sweep" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="var(--scene-transparent)" />
          <stop offset="50%" stop-color="var(--scene-sweep)" />
          <stop offset="100%" stop-color="var(--scene-transparent)" />
        </linearGradient>
        <linearGradient id="ir-scene-ring-band" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--scene-ring-band-hi)" />
          <stop offset="55%" stop-color="var(--scene-ring-band-mid)" />
          <stop offset="100%" stop-color="var(--scene-ring-band-lo)" />
        </linearGradient>
        <linearGradient id="ir-scene-output" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="var(--scene-cyan-line)" />
          <stop offset="100%" stop-color="var(--scene-violet-line)" />
        </linearGradient>
        <filter id="ir-scene-local-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ir-scene-soft-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="10" />
        </filter>
        <mask id="ir-scene-orbit-mask">
          <rect width="1600" height="900" fill="var(--scene-mask-black)" />
          <ellipse cx="1160" cy="390" rx="186" ry="57" fill="none" stroke="var(--scene-mask-white)" stroke-width="2" stroke-dasharray="210 46 94 78" />
        </mask>
        <clipPath id="ir-scene-solar-clip">
          <polygon points="872,542 1050,501 1104,563 917,612" />
        </clipPath>
      </defs>

      <!-- Hallmark · pre-emit critique: P5 H4 E4 S5 R5 V4 -->
      <g class="ir-scene-layer ir-scene-layer--atmosphere">
        <ellipse cx="1190" cy="420" rx="520" ry="390" fill="url(#ir-scene-atmosphere)" />
        <path class="ir-scene-horizon" d="M790 702 C1010 630 1325 646 1595 745" />
        <path class="ir-scene-grid-line" d="M838 679 C1056 620 1320 636 1560 712" />
        <path class="ir-scene-grid-line" d="M900 650 C1080 610 1296 620 1482 675" />
        <path class="ir-scene-grid-line" d="M1030 630 C1142 611 1276 617 1390 648" />
        <path class="ir-scene-grid-line" d="M1030 630 L950 707 M1142 613 L1100 681 M1268 617 L1290 686 M1382 645 L1475 718" />
      </g>

      <g class="ir-scene-layer ir-scene-layer--grid">
        <path class="ir-scene-grid-trunk" d="M1250 390 C1340 374 1408 387 1492 358 C1532 344 1566 337 1615 340" />
        <path class="ir-scene-grid-branch" d="M1392 381 C1438 418 1482 440 1546 438" />
        <path class="ir-scene-grid-branch" d="M1454 371 C1492 326 1540 300 1608 296" />
        <g class="ir-scene-grid-node ir-scene-grid-node--main" transform="translate(1492 358)">
          <circle r="18" /><circle r="7" /><path d="M-28 0H-18M18 0H28M0-28V-18M0 18V28" />
        </g>
        <g class="ir-scene-grid-node" transform="translate(1546 438)"><circle r="9" /><circle r="3" /></g>
        <g class="ir-scene-grid-node" transform="translate(1548 305)"><circle r="7" /><circle r="2.5" /></g>
        <circle class="ir-scene-grid-pulse" cx="0" cy="0" r="3" />
      </g>

      <g class="ir-scene-layer ir-scene-layer--devices">
        <!-- 次要输入：风电 -->
        <g class="ir-scene-wind" transform="translate(1360 220)">
          <ellipse class="ir-scene-device-shadow" cx="0" cy="142" rx="48" ry="10" />
          <path class="ir-scene-wind-tower" d="M-8 20 L-17 142 H18 L8 20 Z" />
          <path class="ir-scene-wind-rim" d="M8 22 18 142" />
          <path class="ir-scene-wind-nacelle" d="M-18-8H23L34 0 21 10H-18Z" />
          <g class="ir-scene-wind-rotor">
            <path d="M0 0 C-9-23 -8-55 0-88 C8-54 8-24 0 0Z" />
            <path d="M0 0 C24-8 56-5 87 8 C52 12 23 9 0 0Z" transform="rotate(120)" />
            <path d="M0 0 C24-8 56-5 87 8 C52 12 23 9 0 0Z" transform="rotate(240)" />
            <circle r="8" />
          </g>
        </g>

        <!-- 次要输入：透视光伏阵列 -->
        <g class="ir-scene-solar">
          <ellipse class="ir-scene-device-shadow" cx="982" cy="616" rx="125" ry="17" />
          <path class="ir-scene-solar-support" d="M912 580 902 622M1018 555l8 42M965 597l-3 28M1070 571l15 32" />
          <g class="ir-scene-solar-panel">
            <polygon points="872,542 1038,504 1082,552 910,596" />
            <path d="M907 534 948 587M945 525 986 577M984 516 1025 567M1022 507 1064 557M890 565 1059 524" />
          </g>
          <g class="ir-scene-solar-panel ir-scene-solar-panel--front">
            <polygon points="917,612 1104,563 1156,620 958,677" />
            <path d="M958 601 1002 664M1001 590 1048 651M1047 578 1094 638M1090 567 1139 625M936 640 1128 587" />
          </g>
          <rect class="ir-scene-solar-sweep" x="830" y="492" width="48" height="190" clip-path="url(#ir-scene-solar-clip)" />
        </g>

        <!-- 设备主角：2.5D 储能柜列 -->
        <g class="ir-scene-storage">
          <ellipse class="ir-scene-device-shadow ir-scene-device-shadow--storage" cx="1192" cy="786" rx="168" ry="25" />
          <g class="ir-scene-cabinet ir-scene-cabinet--rear" transform="translate(1280 625) scale(.84)">
            <polygon class="ir-scene-cabinet-top" points="0,0 92,-22 122,-5 27,20" />
            <polygon class="ir-scene-cabinet-side" points="92,-22 122,-5 122,142 92,168" />
            <path class="ir-scene-cabinet-front" d="M0 0 92-22V168L0 184Z" />
          </g>
          <g class="ir-scene-cabinet ir-scene-cabinet--middle" transform="translate(1210 612) scale(.92)">
            <polygon class="ir-scene-cabinet-top" points="0,0 94,-23 126,-5 28,20" />
            <polygon class="ir-scene-cabinet-side" points="94,-23 126,-5 126,158 94,184" />
            <path class="ir-scene-cabinet-front" d="M0 0 94-23V184L0 201Z" />
            <path class="ir-scene-cabinet-seam" d="M12 34 80 19M12 78 80 63M12 122 80 107" />
          </g>
          <g class="ir-scene-cabinet ir-scene-cabinet--main" transform="translate(1114 602)">
            <polygon class="ir-scene-cabinet-top" points="0,0 108,-27 143,-7 31,23" />
            <polygon class="ir-scene-cabinet-side" points="108,-27 143,-7 143,174 108,204" />
            <path class="ir-scene-cabinet-front" d="M0 0 108-27V204L0 224Z" />
            <path class="ir-scene-cabinet-edge" d="M108-27V204L0 224" />
            <g class="ir-scene-cabinet-modules">
              <path d="M13 31 91 12V50L13 67Z" />
              <path d="M13 75 91 57V95L13 112Z" />
              <path d="M13 119 91 102V140L13 157Z" />
              <path d="M13 164 91 147V184L13 201Z" />
            </g>
            <g class="ir-scene-cabinet-vents">
              <path d="M25 42 76 30M25 49 76 37M25 86 76 74M25 93 76 81M25 130 76 119M25 137 76 126" />
            </g>
            <path class="ir-scene-cabinet-control" d="M98 5 105 3V151L98 153Z" />
            <circle class="ir-scene-storage-led" cx="101.5" cy="22" r="3.2" />
            <circle class="ir-scene-storage-led ir-scene-storage-led--2" cx="101.5" cy="36" r="2.3" />
          </g>
        </g>
      </g>

      <g class="ir-scene-layer ir-scene-layer--paths">
        <path class="ir-scene-input-path" d="M1360 220 C1320 275 1264 315 1199 356" />
        <path class="ir-scene-input-path" d="M1005 575 C1040 520 1080 472 1128 430" />
        <path class="ir-scene-input-path ir-scene-input-path--storage" d="M1188 628 C1182 564 1172 500 1163 459" />
        <path class="ir-scene-output-path" d="M1248 390 C1342 375 1406 388 1492 358" />
      </g>

      <!-- 空心计算装置：背景的推演系统，不是第二个品牌光球 -->
      <g class="ir-scene-layer ir-scene-layer--apparatus">
        <circle cx="1160" cy="390" r="215" fill="url(#ir-scene-core-field)" />
        <ellipse class="ir-scene-apparatus-shadow" cx="1160" cy="493" rx="135" ry="28" />
        <circle class="ir-scene-scan-ring" cx="1160" cy="390" r="108" />
        <circle class="ir-scene-plate" cx="1160" cy="390" r="82" />
        <circle class="ir-scene-plate-inset" cx="1160" cy="390" r="66" />

        <g class="ir-scene-compute-ring">
          <circle class="ir-scene-ring-band" cx="1160" cy="390" r="76" pathLength="100" />
          <circle class="ir-scene-ring-inner" cx="1160" cy="390" r="68" pathLength="100" />
          <circle class="ir-scene-ring-edge" cx="1160" cy="390" r="81" pathLength="100" />
          <circle class="ir-scene-ring-accent" cx="1160" cy="390" r="76" pathLength="100" />
          <g class="ir-scene-ticks">
            <path d="M1160 296V305M1160 475V484M1066 390H1075M1245 390H1254" />
            <path d="M1093.5 323.5l6.4 6.4M1220.1 450.1l6.4 6.4M1226.5 323.5l-6.4 6.4M1099.9 450.1l-6.4 6.4" />
          </g>
        </g>

        <g class="ir-scene-orbit ir-scene-orbit--inner">
          <ellipse cx="1160" cy="390" rx="150" ry="46" />
          <rect x="1072" y="340" width="19" height="7" rx="2" />
          <path class="ir-scene-packet-diamond" d="M1267 411l6 6-6 6-6-6Z" />
        </g>
        <g transform="rotate(25 1160 390)">
          <g class="ir-scene-orbit ir-scene-orbit--outer" mask="url(#ir-scene-orbit-mask)">
            <ellipse cx="1160" cy="390" rx="186" ry="57" />
            <rect x="1240" y="330" width="22" height="8" rx="2" />
            <path class="ir-scene-packet-diamond" d="M1017 415l7 7-7 7-7-7Z" />
          </g>
        </g>

        <g class="ir-scene-locator">
          <circle cx="1160" cy="390" r="5" />
          <path d="M1160 374V382M1160 398V406M1144 390H1152M1168 390H1176" />
        </g>
        <path class="ir-scene-arrival ir-scene-arrival--wind" d="M1116 328 A76 76 0 0 1 1150 315" />
        <path class="ir-scene-arrival ir-scene-arrival--solar" d="M1090 420 A76 76 0 0 1 1085 384" />
        <path class="ir-scene-arrival ir-scene-arrival--storage" d="M1138 463 A76 76 0 0 1 1178 464" />
        <path class="ir-scene-arrival ir-scene-arrival--output" d="M1224 350 A76 76 0 0 1 1235 382" />
      </g>
    </svg>

    <canvas ref="canvasEl" class="ir-welcome-scene__canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const VB_W = 1600
const VB_H = 900
const CORE = { x: 1160, y: 390 }
const ROUTES = {
  wind: { start: { x: 1360, y: 220 }, end: CORE, control: { x: 1288, y: 318 }, output: false },
  solar: { start: { x: 1005, y: 575 }, end: CORE, control: { x: 1050, y: 478 }, output: false },
  storage: { start: { x: 1188, y: 628 }, end: CORE, control: { x: 1178, y: 510 }, output: false },
  grid: { start: CORE, end: { x: 1492, y: 358 }, control: { x: 1340, y: 366 }, output: true },
}
const ROUTE_SEQUENCE = ['storage', 'wind', 'storage', 'solar', 'grid', 'storage', 'grid']

const canvasEl = ref(null)
let raf = 0
let ctx = null
let width = 0
let height = 0
let dpr = 1
let scale = 1
let offsetX = 0
let offsetY = 0
let packets = []
let running = false
let reduced = false
let lastTime = 0
let colors = { input: '', output: '', outputAccent: '' }

function packetCountFor(w, h) {
  if (w < 768) return 0
  const area = w * h
  if (area >= 1_900_000) return 15
  if (area >= 1_100_000) return 12
  return 8
}

function buildPacket(index, count) {
  const key = ROUTE_SEQUENCE[index % ROUTE_SEQUENCE.length]
  const route = ROUTES[key]
  return {
    key,
    route,
    t: (index / Math.max(1, count)) * 0.92,
    speed: route.output ? 0.115 : key === 'storage' ? 0.092 : 0.078,
    alpha: key === 'storage' ? 0.82 : 0.62,
    lane: ((index % 3) - 1) * 4,
  }
}

function resetPacket(packet) {
  const routeIndex = ROUTE_SEQUENCE.indexOf(packet.key)
  packet.t = -0.12 - ((routeIndex + packets.indexOf(packet)) % 5) * 0.08
}

function pointAt(packet, t) {
  const { start, end, control } = packet.route
  const mt = 1 - t
  return {
    x: mt * mt * start.x + 2 * mt * t * (control.x + packet.lane) + t * t * end.x,
    y: mt * mt * start.y + 2 * mt * t * (control.y - packet.lane) + t * t * end.y,
  }
}

function readCanvasColors(el) {
  const styles = getComputedStyle(el)
  colors = {
    input: styles.getPropertyValue('--scene-particle-input').trim(),
    output: styles.getPropertyValue('--scene-particle-output').trim(),
    outputAccent: styles.getPropertyValue('--scene-particle-output-accent').trim(),
  }
}

function resize() {
  const el = canvasEl.value
  if (!el) return
  dpr = Math.min(window.devicePixelRatio || 1, 1.5)
  width = el.clientWidth
  height = el.clientHeight
  if (!width || !height) {
    ctx = null
    packets = []
    return
  }
  el.width = Math.round(width * dpr)
  el.height = Math.round(height * dpr)
  try {
    ctx = el.getContext('2d')
  } catch (error) {
    ctx = null
  }
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  scale = Math.max(width / VB_W, height / VB_H)
  offsetX = (width - VB_W * scale) / 2
  offsetY = (height - VB_H * scale) / 2
  readCanvasColors(el)
  const count = packetCountFor(width, height)
  packets = Array.from({ length: count }, (_, index) => buildPacket(index, count))
}

function drawInputPacket(packet, previous, current, fade) {
  ctx.globalAlpha = packet.alpha * fade
  ctx.strokeStyle = colors.input
  ctx.lineWidth = 1.2
  ctx.beginPath()
  ctx.moveTo(previous.x * scale + offsetX, previous.y * scale + offsetY)
  ctx.lineTo(current.x * scale + offsetX, current.y * scale + offsetY)
  ctx.stroke()
}

function drawOutputPacket(packet, current, fade) {
  const x = current.x * scale + offsetX
  const y = current.y * scale + offsetY
  const size = 3.2 * Math.min(scale, 1.35)
  ctx.globalAlpha = packet.alpha * fade
  ctx.fillStyle = colors.outputAccent
  ctx.strokeStyle = colors.output
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(x, y - size)
  ctx.lineTo(x + size * 1.45, y)
  ctx.lineTo(x, y + size)
  ctx.lineTo(x - size * 1.45, y)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
}

function frame(time) {
  if (!ctx || !running) return
  const delta = Math.min(40, lastTime ? time - lastTime : 16.7) / 1000
  lastTime = time
  ctx.clearRect(0, 0, width, height)
  for (const packet of packets) {
    packet.t += packet.speed * delta
    if (packet.t >= 1) resetPacket(packet)
    if (packet.t <= 0) continue
    const current = pointAt(packet, packet.t)
    const previous = pointAt(packet, Math.max(0, packet.t - 0.035))
    const fade = Math.min(1, packet.t * 7) * Math.min(1, (1 - packet.t) * 7)
    if (packet.route.output) drawOutputPacket(packet, current, fade)
    else drawInputPacket(packet, previous, current, fade)
  }
  ctx.globalAlpha = 1
  raf = window.requestAnimationFrame(frame)
}

function start() {
  if (reduced || typeof window === 'undefined' || !canvasEl.value) return
  resize()
  if (!ctx || packets.length === 0) return
  running = true
  lastTime = 0
  window.cancelAnimationFrame(raf)
  raf = window.requestAnimationFrame(frame)
}

function pause() {
  running = false
  lastTime = 0
  if (typeof window !== 'undefined') window.cancelAnimationFrame(raf)
}

function onVisibility() {
  if (document.hidden) pause()
  else if (!reduced) start()
}

onMounted(() => {
  if (typeof window === 'undefined') return
  reduced = Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  start()
  window.addEventListener('resize', start)
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  pause()
  window.removeEventListener('resize', start)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
/* Hallmark · component: ambient scene · genre: atmospheric industrial · theme: XC dark
 * states: static · active · reduced-motion · laptop · mobile
 * contrast: decorative background remains subordinate to foreground content
 */
.ir-welcome-scene {
  --scene-transparent: rgba(0, 0, 0, 0);
  --scene-mask-black: rgb(0, 0, 0);
  --scene-mask-white: rgb(255, 255, 255);
  --scene-atmosphere-core: rgba(0, 176, 185, 0.105);
  --scene-atmosphere-mid: rgba(34, 177, 253, 0.025);
  --scene-core-center: rgba(12, 36, 57, 0.28);
  --scene-core-edge: rgba(3, 12, 27, 0.04);
  --scene-metal-front-hi: rgba(84, 111, 136, 0.25);
  --scene-metal-front-lo: rgba(16, 29, 47, 0.74);
  --scene-metal-side-hi: rgba(34, 61, 82, 0.50);
  --scene-metal-side-lo: rgba(8, 18, 33, 0.86);
  --scene-metal-top-hi: rgba(104, 139, 160, 0.24);
  --scene-metal-top-lo: rgba(21, 42, 60, 0.58);
  --scene-panel-hi: rgba(25, 91, 123, 0.45);
  --scene-panel-lo: rgba(10, 29, 58, 0.78);
  --scene-sweep: rgba(122, 224, 255, 0.38);
  --scene-ring-band-hi: rgba(38, 106, 133, 0.72);
  --scene-ring-band-mid: rgba(12, 42, 66, 0.92);
  --scene-ring-band-lo: rgba(36, 29, 79, 0.70);
  --scene-cyan-line: rgba(0, 240, 253, 0.55);
  --scene-violet-line: rgba(154, 100, 255, 0.50);
  --scene-particle-input: rgba(92, 210, 239, 0.72);
  --scene-particle-output: rgba(183, 155, 255, 0.74);
  --scene-particle-output-accent: rgba(96, 205, 248, 0.48);
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.ir-welcome-scene__svg,
.ir-welcome-scene__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.ir-welcome-scene__canvas { z-index: 3; }

.ir-scene-horizon,
.ir-scene-grid-line,
.ir-scene-grid-trunk,
.ir-scene-grid-branch,
.ir-scene-input-path,
.ir-scene-output-path,
.ir-scene-grid-node path {
  fill: none;
  vector-effect: non-scaling-stroke;
}
.ir-scene-horizon { stroke: var(--xc-border-soft); stroke-width: 1; opacity: 0.24; }
.ir-scene-grid-line { stroke: var(--xc-border-card); stroke-width: 0.7; opacity: 0.22; }
.ir-scene-grid-trunk { stroke: url(#ir-scene-output); stroke-width: 1.5; opacity: 0.44; }
.ir-scene-grid-branch { stroke: var(--xc-border-accent); stroke-width: 0.8; opacity: 0.25; }
.ir-scene-grid-node circle:first-child { fill: rgba(8, 20, 38, 0.72); stroke: var(--xc-border-accent); stroke-width: 1; }
.ir-scene-grid-node circle:nth-child(2) { fill: var(--xc-brand-violet-2); opacity: 0.5; }
.ir-scene-grid-node path { stroke: var(--xc-border-accent); stroke-width: 0.8; opacity: 0.42; }
.ir-scene-grid-node--main circle:first-child { stroke: var(--xc-brand-violet-2); opacity: 0.75; }
.ir-scene-grid-pulse {
  fill: var(--xc-brand-violet-2);
  filter: url(#ir-scene-local-glow);
  offset-path: path('M1250 390 C1340 374 1408 387 1492 358 C1532 344 1566 337 1615 340');
  animation: ir-scene-grid-run 9s linear infinite;
}

.ir-scene-device-shadow { fill: rgba(0, 0, 0, 0.34); }
.ir-scene-device-shadow--storage { fill: rgba(0, 0, 0, 0.46); }
.ir-scene-wind { opacity: 0.58; }
.ir-scene-wind-tower { fill: url(#ir-scene-metal-front); stroke: rgba(167, 202, 220, 0.34); stroke-width: 1; }
.ir-scene-wind-rim { fill: none; stroke: var(--xc-brand-cyan-2); stroke-width: 1.2; opacity: 0.5; }
.ir-scene-wind-nacelle { fill: url(#ir-scene-metal-top); stroke: rgba(180, 214, 229, 0.34); stroke-width: 1; }
.ir-scene-wind-rotor {
  transform-box: fill-box;
  transform-origin: center;
  animation: ir-scene-spin 26s linear infinite;
}
.ir-scene-wind-rotor path { fill: rgba(111, 153, 177, 0.34); stroke: rgba(184, 217, 232, 0.38); stroke-width: 0.9; }
.ir-scene-wind-rotor circle { fill: rgba(13, 37, 57, 0.95); stroke: var(--xc-brand-cyan-2); stroke-width: 1.2; }

.ir-scene-solar { opacity: 0.68; }
.ir-scene-solar-support { fill: none; stroke: rgba(133, 169, 187, 0.28); stroke-width: 2; }
.ir-scene-solar-panel polygon { fill: url(#ir-scene-panel); stroke: rgba(93, 196, 222, 0.48); stroke-width: 1.1; }
.ir-scene-solar-panel path { fill: none; stroke: rgba(93, 186, 215, 0.22); stroke-width: 0.75; }
.ir-scene-solar-panel--front { opacity: 0.9; }
.ir-scene-solar-sweep {
  fill: url(#ir-scene-sweep);
  transform: translateX(-90px) skewX(-10deg);
  animation: ir-scene-solar-sweep 10s var(--xc-ease-in-out) infinite;
  animation-delay: -2.5s;
}

.ir-scene-cabinet--rear { opacity: 0.28; }
.ir-scene-cabinet--middle { opacity: 0.48; }
.ir-scene-cabinet--main { opacity: 0.9; }
.ir-scene-cabinet-top { fill: url(#ir-scene-metal-top); stroke: rgba(139, 185, 204, 0.32); stroke-width: 1; }
.ir-scene-cabinet-side { fill: url(#ir-scene-metal-side); stroke: rgba(83, 139, 165, 0.35); stroke-width: 1; }
.ir-scene-cabinet-front { fill: url(#ir-scene-metal-front); stroke: rgba(139, 185, 204, 0.46); stroke-width: 1.1; }
.ir-scene-cabinet-edge { fill: none; stroke: var(--xc-brand-cyan-2); stroke-width: 1.25; opacity: 0.56; }
.ir-scene-cabinet-seam,
.ir-scene-cabinet-vents path { fill: none; stroke: rgba(151, 193, 210, 0.23); stroke-width: 0.8; }
.ir-scene-cabinet-modules path { fill: rgba(4, 16, 29, 0.46); stroke: rgba(83, 152, 178, 0.28); stroke-width: 0.75; }
.ir-scene-cabinet-control { fill: rgba(0, 176, 185, 0.16); stroke: rgba(0, 240, 253, 0.42); stroke-width: 0.7; }
.ir-scene-storage-led { fill: var(--xc-brand-cyan); filter: url(#ir-scene-local-glow); animation: ir-scene-led 7s var(--xc-ease-in-out) infinite; }
.ir-scene-storage-led--2 { fill: var(--xc-accent-blue); animation-delay: -3.4s; }

.ir-scene-input-path { stroke: rgba(66, 166, 195, 0.20); stroke-width: 0.9; stroke-dasharray: 3 9; }
.ir-scene-input-path--storage { stroke: rgba(0, 240, 253, 0.29); stroke-width: 1.2; }
.ir-scene-output-path { stroke: url(#ir-scene-output); stroke-width: 1.1; stroke-dasharray: 7 10; opacity: 0.34; }

.ir-scene-apparatus-shadow { fill: rgba(0, 0, 0, 0.25); filter: url(#ir-scene-soft-glow); }
.ir-scene-scan-ring { fill: none; stroke: rgba(0, 240, 253, 0.24); stroke-width: 1; transform-origin: 1160px 390px; animation: ir-scene-scan 10s var(--xc-ease-out) infinite; }
.ir-scene-plate { fill: rgba(5, 17, 31, 0.82); stroke: rgba(66, 166, 195, 0.20); stroke-width: 1; }
.ir-scene-plate-inset { fill: rgba(8, 24, 39, 0.68); stroke: rgba(212, 225, 244, 0.08); stroke-width: 1; }
.ir-scene-compute-ring,
.ir-scene-orbit { transform-box: view-box; transform-origin: 1160px 390px; will-change: transform; }
.ir-scene-compute-ring { animation: ir-scene-spin 31s linear infinite; }
.ir-scene-ring-band { fill: none; stroke: url(#ir-scene-ring-band); stroke-width: 9; stroke-linecap: round; stroke-dasharray: 17 5 11 7 24 8 9 19; }
.ir-scene-ring-inner { fill: none; stroke: rgba(122, 224, 255, 0.28); stroke-width: 0.9; stroke-dasharray: 22 8 12 14 28 16; }
.ir-scene-ring-edge { fill: none; stroke: rgba(212, 225, 244, 0.14); stroke-width: 0.8; stroke-dasharray: 31 10 17 18 8 16; }
.ir-scene-ring-accent { fill: none; stroke: var(--xc-brand-violet-2); stroke-width: 2.2; stroke-linecap: round; stroke-dasharray: 7 93; opacity: 0.52; }
.ir-scene-ticks path { fill: none; stroke: rgba(122, 224, 255, 0.38); stroke-width: 1; }
.ir-scene-orbit ellipse { fill: none; stroke: rgba(85, 187, 216, 0.26); stroke-width: 1; stroke-dasharray: 4 7 28 12; }
.ir-scene-orbit rect { fill: rgba(0, 240, 253, 0.48); stroke: rgba(122, 224, 255, 0.54); stroke-width: 0.8; }
.ir-scene-packet-diamond { fill: rgba(154, 100, 255, 0.52); stroke: rgba(183, 155, 255, 0.65); stroke-width: 0.8; }
.ir-scene-orbit--inner { animation: ir-scene-spin 27s linear infinite; }
.ir-scene-orbit--outer { animation: ir-scene-spin-rev 41s linear infinite; }
.ir-scene-locator circle { fill: var(--xc-brand-cyan); filter: url(#ir-scene-local-glow); }
.ir-scene-locator path { fill: none; stroke: rgba(122, 224, 255, 0.52); stroke-width: 1; }
.ir-scene-arrival { fill: none; stroke-width: 3; stroke-linecap: round; opacity: 0; filter: url(#ir-scene-local-glow); animation: ir-scene-arrival 14s var(--xc-ease-out) infinite; }
.ir-scene-arrival--wind { stroke: var(--xc-brand-cyan-2); animation-delay: -2s; }
.ir-scene-arrival--solar { stroke: var(--xc-accent-blue); animation-delay: -7s; }
.ir-scene-arrival--storage { stroke: var(--xc-brand-cyan); animation-delay: -11s; }
.ir-scene-arrival--output { stroke: var(--xc-brand-violet-2); animation-delay: -4.5s; }

@keyframes ir-scene-spin { to { transform: rotate(360deg); } }
@keyframes ir-scene-spin-rev { to { transform: rotate(-360deg); } }
@keyframes ir-scene-led { 0%, 72%, 100% { opacity: 0.34; } 78%, 90% { opacity: 0.95; } }
@keyframes ir-scene-solar-sweep {
  0%, 12% { transform: translateX(-90px) skewX(-10deg); opacity: 0; }
  18% { opacity: 0.75; }
  36% { transform: translateX(300px) skewX(-10deg); opacity: 0; }
  100% { transform: translateX(300px) skewX(-10deg); opacity: 0; }
}
@keyframes ir-scene-grid-run {
  0%, 20% { offset-distance: 0%; opacity: 0; }
  26% { opacity: 0.7; }
  50% { offset-distance: 100%; opacity: 0; }
  100% { offset-distance: 100%; opacity: 0; }
}
@keyframes ir-scene-scan {
  0%, 66% { transform: scale(0.86); opacity: 0; }
  70% { opacity: 0.32; }
  88%, 100% { transform: scale(1.48); opacity: 0; }
}
@keyframes ir-scene-arrival {
  0%, 76%, 100% { opacity: 0; }
  80% { opacity: 0.75; }
  88% { opacity: 0; }
}

@media (max-width: 1199px) {
  .ir-scene-layer--devices { transform: translateX(80px); }
  .ir-scene-layer--apparatus,
  .ir-scene-layer--paths,
  .ir-scene-layer--grid { transform: translateX(55px); }
  .ir-scene-wind,
  .ir-scene-solar { opacity: 0.36; }
  .ir-welcome-scene__canvas { opacity: 0.72; }
}

@media (max-width: 767px) {
  .ir-scene-layer--devices,
  .ir-scene-layer--grid,
  .ir-scene-layer--paths,
  .ir-welcome-scene__canvas { display: none; }
  .ir-scene-layer--apparatus { transform: translate(310px, 20px) scale(1.12); transform-origin: 1160px 390px; opacity: 0.25; }
  .ir-scene-layer--atmosphere { transform: translateX(180px); opacity: 0.58; }
  .ir-scene-arrival,
  .ir-scene-orbit { animation: none; }
}

@media (prefers-reduced-motion: reduce) {
  .ir-welcome-scene *,
  .ir-welcome-scene *::before,
  .ir-welcome-scene *::after {
    animation: none !important;
  }
  .ir-scene-scan-ring,
  .ir-scene-grid-pulse,
  .ir-scene-arrival,
  .ir-scene-solar-sweep { opacity: 0; }
}
</style>
