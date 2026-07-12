<template>
  <div 
    class="animation-player" 
    :class="{ 'is-playing': playing }"
    @mouseenter="hovering = true"
    @mouseleave="hovering = false"
  >
    <iframe ref="frame" class="animation-player__frame" :class="{ 'pointer-events-none': isDragging }" :srcdoc="html" sandbox="allow-scripts" title="教学动画"></iframe>
    
    <div class="animation-player__overlay" :class="{ 'is-hidden': !hovering && playbackState === 'playing' }">
      <div class="animation-player__subtitle-wrapper">
        <div 
          v-if="narrationHealthy && subtitleVisible && currentCue" 
          class="animation-player__subtitle"
          :style="{ transform: `translate(${subtitleX}px, ${subtitleY}px)` }"
          @mousedown.stop="onSubtitleDragStart"
          @touchstart.stop="onSubtitleDragStart"
        >
          <span>{{ currentCue.text }}</span>
        </div>
      </div>
      
      <div class="animation-player__controls">
        <div class="animation-player__playback">
          <button type="button" :disabled="!narrationHealthy" :title="playing ? '暂停' : '播放'" @click="togglePlayback" class="btn-icon">
            <svg v-if="playing" viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            <svg v-else viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </button>
          <button type="button" title="重播" @click="replay" class="btn-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>
          </button>
          <span class="time-text">{{ formatTime(currentMs) }}</span>
          <input class="animation-player__progress" type="range" min="0" :max="durationMs" step="100" :value="currentMs" aria-label="动画进度" @input="seek">
          <span class="time-text">{{ formatTime(durationMs) }}</span>
          
          <button type="button" :disabled="!narrationHealthy" :title="subtitleVisible ? '隐藏字幕' : '显示字幕'" @click="subtitleVisible = !subtitleVisible" class="btn-icon btn-subtitle" :class="{ 'is-active': subtitleVisible }">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-8 7H9.5v-.5h-2v3h2V13H11v1c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1zm7 0h-1.5v-.5h-2v3h2V13H18v1c0 .55-.45 1-1 1h-3c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1z"/></svg>
          </button>
          <div class="volume-control">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
            <input type="range" min="0" max="1" step="0.05" v-model.number="volume" aria-label="音量" class="volume-slider">
          </div>
        </div>
        
        <div class="animation-player__export">
          <select v-model="selectedQuality" aria-label="导出清晰度" class="export-select">
            <option value="1080p">1080p</option><option value="720p">720p</option>
          </select>
          <button type="button" class="btn-export" :disabled="!exportSupported || activeExport.status === 'rendering'" @click="handleExport">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" v-if="activeExport.status === 'ready'"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            <svg class="icon-spin" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" v-else-if="activeExport.status === 'rendering'"><path d="M12 4V2C6.48 2 2 6.48 2 12h2c0-4.41 3.59-8 8-8zm8 8c0-4.41-3.59-8-8-8v2c4.41 0 8 3.59 8 8h2z"/></svg>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" v-else><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            {{ exportLabel }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="narrationHealthy && playbackNotice && !audioPendingStatus" class="animation-player__notice">{{ playbackNotice }}</div>
    <div v-if="audioPendingStatus" class="animation-player__notice bg-orange-50/90 text-orange-800 border-orange-200 backdrop-blur" style="border: 1px solid currentColor;">
      语音正在后台努力合成中，当前为无声预览模式...
    </div>
    
    <!-- Refresh Button Toast -->
    <div v-if="showAudioReadyToast" class="absolute top-4 left-1/2 -translate-x-1/2 z-[100] flex items-center gap-3 px-4 py-2 bg-white/90 backdrop-blur shadow-lg rounded-full border border-green-200" style="animation: slide-down 0.3s ease-out forwards;">
      <span class="text-sm font-medium text-green-700">语音合成已就绪！</span>
      <button type="button" @click="applyNewAudio" class="text-xs px-3 py-1 bg-green-500 hover:bg-green-600 text-white rounded-full transition-colors shadow-sm">
        点击刷新体验
      </button>
      <button type="button" @click="showAudioReadyToast = false" class="text-green-400 hover:text-green-600 ml-1">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
    </div>

    <div v-if="!narrationHealthy" class="animation-player__invalid">讲解数据异常，请重新生成该动画</div>
    <div v-if="bridgeError" class="animation-player__error">{{ bridgeError }}</div>
    <div v-if="exportError" class="animation-player__error">{{ exportError }}</div>
    
    <audio ref="audio" :src="audioSrc" preload="auto" @loadedmetadata="onAudioLoadedMetadata" @canplay="onAudioCanPlay" @error="onAudioError" @ended="onAudioEnded"></audio>
  </div>
</template>

<style scoped>
@keyframes slide-down {
  from { opacity: 0; transform: translate(-50%, -10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createAnimationExport, getAnimationExports, getResource, type AnimationExportQuality, type AnimationExportState } from '@/api/resource'
import { PYTHON_AI_BASE } from '@/api/request'
import {
  advanceSilentTime,
  createSilentAnchor,
  findCueAtTime,
  narrationNotice,
  narrationIsHealthy,
  resolvePlayableAudioUrl,
  shouldUseAudioClock,
  type NarrationLike,
  type PlaybackState,
} from '@/utils/animationPlayback'

interface Cue { beatIndex: number; startMs: number; endMs: number; text: string }
interface Narration extends NarrationLike {
  version: number
  voice: string
  audioUrl: string
  duration: number
  cues: Cue[]
}

const props = defineProps<{ resourceId: number; html: string; narration: Narration; videoExports?: Record<string, AnimationExportState>; isDragging?: boolean }>()
const frame = ref<HTMLIFrameElement | null>(null)
const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
const hovering = ref(false)
const playbackState = ref<PlaybackState>('idle')
const subtitleVisible = ref(true)
const currentMs = ref(0)
const volume = ref(1)
const audioFailed = ref(false)
const bridgeError = ref('')
const exportError = ref('')
const selectedQuality = ref<AnimationExportQuality>('1080p')
const exports = ref<Record<AnimationExportQuality, AnimationExportState>>({
  '1080p': props.videoExports?.['1080p'] || { status: 'idle' },
  '720p': props.videoExports?.['720p'] || { status: 'idle' },
})

const activeNarration = ref<Narration>(props.narration)
const audioPendingStatus = ref(false)
const showAudioReadyToast = ref(false)
let fetchedNarration: Narration | null = null

watch(() => props.narration, (newVal) => {
  activeNarration.value = newVal
  audioPendingStatus.value = newVal.audioStatus === 'pending'
}, { immediate: true })

let audioPollTimer: number | undefined

async function pollAudioReady() {
  if (!audioPendingStatus.value) return
  try {
    const res = await getResource(props.resourceId)
    const content = typeof res.data.moduleData === 'string' ? JSON.parse(res.data.moduleData) : res.data.moduleData
    if (content?.narration && content.narration.audioStatus !== 'pending') {
      audioPendingStatus.value = false
      showAudioReadyToast.value = true
      fetchedNarration = content.narration
    } else {
      audioPollTimer = window.setTimeout(pollAudioReady, 3000)
    }
  } catch (e) {
    audioPollTimer = window.setTimeout(pollAudioReady, 5000)
  }
}

watch(audioPendingStatus, (pending) => {
  if (pending) {
    clearTimeout(audioPollTimer)
    audioPollTimer = window.setTimeout(pollAudioReady, 3000)
  } else {
    clearTimeout(audioPollTimer)
  }
}, { immediate: true })

function applyNewAudio() {
  if (fetchedNarration) {
    activeNarration.value = fetchedNarration
    showAudioReadyToast.value = false
    // reset playback
    endPlayback()
    currentMs.value = 0
    audioFailed.value = false
  }
}

let rafId: number | undefined
let pollTimer: number | undefined
let lastBeatIndex = -1
let silentAnchor = createSilentAnchor(0)
let clockMode: 'audio' | 'silent' = 'silent'

const subtitleX = ref(0)
const subtitleY = ref(0)
let isDraggingSubtitle = false
let startDragX = 0
let startDragY = 0

function onSubtitleDragStart(e: MouseEvent | TouchEvent) {
  isDraggingSubtitle = true
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  startDragX = clientX - subtitleX.value
  startDragY = clientY - subtitleY.value
  document.addEventListener('mousemove', onSubtitleDragMove)
  document.addEventListener('touchmove', onSubtitleDragMove, { passive: false })
  document.addEventListener('mouseup', onSubtitleDragEnd)
  document.addEventListener('touchend', onSubtitleDragEnd)
}

function onSubtitleDragMove(e: MouseEvent | TouchEvent) {
  if (!isDraggingSubtitle) return
  if (e.cancelable) e.preventDefault()
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  subtitleX.value = clientX - startDragX
  subtitleY.value = clientY - startDragY
}

function onSubtitleDragEnd() {
  isDraggingSubtitle = false
  document.removeEventListener('mousemove', onSubtitleDragMove)
  document.removeEventListener('touchmove', onSubtitleDragMove)
  document.removeEventListener('mouseup', onSubtitleDragEnd)
  document.removeEventListener('touchend', onSubtitleDragEnd)
}

const durationMs = computed(() => Math.max(1, Math.round(activeNarration.value.duration * 1000)))
const currentCue = computed(() => findCueAtTime(activeNarration.value.cues, currentMs.value))
const audioSrc = computed(() => {
  if (!shouldUseAudioClock(activeNarration.value, audioFailed.value)) return undefined
  return resolvePlayableAudioUrl(activeNarration.value.audioUrl, PYTHON_AI_BASE)
})
const playbackNotice = computed(() => narrationNotice(activeNarration.value, audioFailed.value))
const narrationHealthy = computed(() => narrationIsHealthy(activeNarration.value))
const exportSupported = computed(() => narrationHealthy.value && !audioPendingStatus.value)
const activeExport = computed(() => exports.value[selectedQuality.value])
const exportLabel = computed(() => ({ idle: '导出视频', rendering: '生成中...', ready: '下载视频', failed: '重试导出' }[activeExport.value.status]))

function send(action: string, extra: Record<string, unknown> = {}) {
  frame.value?.contentWindow?.postMessage({ type: '__AURA_LEGACY_CONTROL__', action, ...extra }, '*')
}

function onFrameMessage(event: MessageEvent) {
  if (event.source !== frame.value?.contentWindow) return
  const message = event.data
  if (!message || typeof message !== 'object' || message.type !== '__AURA_LEGACY_READY__') return
  if (message.bridgeReady === false) {
    bridgeError.value = typeof message.error === 'string' && message.error
      ? `动画桥接初始化失败：${message.error}`
      : '动画桥接初始化失败'
    return
  }
  if (message.gsapReady === false) {
    bridgeError.value = '动画引擎未能加载，请检查网络后重试'
    return
  }
  bridgeError.value = ''
}

function formatTime(ms: number) {
  const total = Math.floor(ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

function cleanupClock() {
  if (rafId !== undefined) {
    cancelAnimationFrame(rafId)
    rafId = undefined
  }
}

function syncBeatIfChanged() {
  const beatIndex = currentCue.value?.beatIndex ?? -1
  if (beatIndex >= 0 && beatIndex !== lastBeatIndex) {
    lastBeatIndex = beatIndex
    send('beat', { beatIndex })
  }
}

function tick(now: number) {
  if (playbackState.value !== 'playing') return

  if (clockMode === 'audio' && audio.value) {
    currentMs.value = audio.value.currentTime * 1000
  } else {
    currentMs.value = advanceSilentTime(silentAnchor.silentStartMs, silentAnchor.silentStartPerf, now, durationMs.value)
  }

  syncBeatIfChanged()

  if (currentMs.value >= durationMs.value) {
    endPlayback()
    return
  }

  rafId = requestAnimationFrame(tick)
}

function startSilentClock() {
  clockMode = 'silent'
  silentAnchor = createSilentAnchor(currentMs.value)
  audio.value?.pause()
  send('play')
  cleanupClock()
  rafId = requestAnimationFrame(tick)
}

function endPlayback() {
  playbackState.value = 'ended'
  playing.value = false
  cleanupClock()
  currentMs.value = durationMs.value
  audio.value?.pause()
  send('pause', { paused: true })
}

async function startPlayback() {
  if (currentMs.value >= durationMs.value) {
    currentMs.value = 0
    lastBeatIndex = -1
    silentAnchor = createSilentAnchor(0)
    if (audio.value && Number.isFinite(audio.value.duration)) audio.value.currentTime = 0
  }

  playbackState.value = 'playing'
  playing.value = true

  if (shouldUseAudioClock(activeNarration.value, audioFailed.value) && audio.value) {
    clockMode = 'audio'
    if (Number.isFinite(currentMs.value) && Number.isFinite(audio.value.duration)) {
      audio.value.currentTime = currentMs.value / 1000
    }
    try {
      await audio.value.play()
      send('play')
      cleanupClock()
      rafId = requestAnimationFrame(tick)
      return
    } catch (err) {
      audioFailed.value = true
    }
  }

  startSilentClock()
}

function pausePlayback() {
  if (playbackState.value !== 'playing') return

  playbackState.value = 'paused'
  playing.value = false
  cleanupClock()

  if (clockMode === 'audio' && audio.value) {
    currentMs.value = audio.value.currentTime * 1000
    audio.value.pause()
  } else {
    currentMs.value = advanceSilentTime(
      silentAnchor.silentStartMs,
      silentAnchor.silentStartPerf,
      performance.now(),
      durationMs.value,
    )
    silentAnchor = createSilentAnchor(currentMs.value)
  }

  send('pause', { paused: true })
}

async function togglePlayback() {
  if (playbackState.value === 'playing') {
    pausePlayback()
    return
  }
  await startPlayback()
}

function replay() {
  cleanupClock()
  currentMs.value = 0
  lastBeatIndex = -1
  silentAnchor = createSilentAnchor(0)
  if (audio.value) audio.value.currentTime = 0
  send('replay')
  void startPlayback()
}

function seek(event: Event) {
  const nextMs = Number((event.target as HTMLInputElement).value)
  currentMs.value = nextMs
  silentAnchor = createSilentAnchor(nextMs)
  lastBeatIndex = -1

  if (audio.value && clockMode === 'audio' && shouldUseAudioClock(activeNarration.value, audioFailed.value)) {
    audio.value.currentTime = nextMs / 1000
  }

  const cue = findCueAtTime(activeNarration.value.cues, nextMs)
  send('seek', { beatIndex: cue?.beatIndex ?? 0 })
  lastBeatIndex = cue?.beatIndex ?? -1
}

function onAudioLoadedMetadata() {
  if (!audio.value) return
  const audioDurationMs = Math.round(audio.value.duration * 1000)
  if (Number.isFinite(audioDurationMs) && audioDurationMs > 0 && Math.abs(audioDurationMs - durationMs.value) > 500) {
    // narration.duration 为准，仅校验音频可加载
  }
}

function onAudioCanPlay() {
  if (playbackState.value === 'playing' && clockMode === 'audio' && audio.value?.paused) {
    void audio.value.play().catch(() => {
      audioFailed.value = true
      startSilentClock()
    })
  }
}

function onAudioError() {
  audioFailed.value = true
  if (playbackState.value === 'playing' && clockMode === 'audio') {
    startSilentClock()
  }
}

function onAudioEnded() {
  endPlayback()
}

const MAX_POLL_MS = 10 * 60 * 1000 // 10 minutes max polling
let pollStartedAt = 0
let pollInterval = 2000

async function refreshExports() {
  const result = await getAnimationExports(props.resourceId)
  exports.value = result.qualities
  const active = exports.value[selectedQuality.value]
  if (active?.status === 'failed' && active.error) exportError.value = active.error
  const stillRendering = Object.values(exports.value).some(state => state.status === 'rendering')
  if (stillRendering) {
    if (Date.now() - pollStartedAt > MAX_POLL_MS) {
      // Timeout: stop polling and show error
      exportError.value = '导出超时，请重试'
      exports.value[selectedQuality.value] = { ...exports.value[selectedQuality.value], status: 'failed' as const }
      return
    }
    pollInterval = Math.min(pollInterval * 1.3, 10000) // gradually slow down, cap at 10s
    pollTimer = window.setTimeout(refreshExports, pollInterval)
  }
}

async function handleExport() {
  exportError.value = ''
  if (!exportSupported.value) { exportError.value = '当前动画的讲解数据已损坏，请重新生成后导出'; return }
  const state = activeExport.value
  if (state.status === 'ready' && state.url) { window.open(state.url, '_blank'); return }
  try {
    const result = await createAnimationExport(props.resourceId, selectedQuality.value)
    exports.value = result.qualities
    const failed = result.qualities?.[selectedQuality.value]
    if (failed?.status === 'failed' && failed.error) exportError.value = failed.error
    window.clearTimeout(pollTimer); pollStartedAt = Date.now(); pollInterval = 2000; pollTimer = window.setTimeout(refreshExports, 1500)
  } catch (error) {
    exportError.value = error instanceof Error ? error.message : '视频导出失败'
  }
}

watch(volume, value => { if (audio.value) audio.value.volume = value })
watch(() => props.html, () => { bridgeError.value = '' })
watch(() => props.narration, () => {
  audioFailed.value = false
  lastBeatIndex = -1
  cleanupClock()
  playbackState.value = 'idle'
  playing.value = false
  currentMs.value = 0
  silentAnchor = createSilentAnchor(0)
}, { deep: true })

onMounted(() => {
  window.addEventListener('message', onFrameMessage)
  if (Object.values(exports.value).some(state => state.status === 'rendering')) {
    pollStartedAt = Date.now(); pollInterval = 2000
    pollTimer = window.setTimeout(refreshExports, 2000)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onFrameMessage)
  cleanupClock()
  window.clearTimeout(pollTimer)
})
</script>

<style scoped>
/* 
 * Layout strategy: .animation-player is ALWAYS flex-column.
 * The iframe has its own aspect-ratio so it sizes itself.
 * In wide mode: overlay is position:absolute over the iframe.
 * In narrow mode (@container): overlay becomes position:static, flowing below iframe.
 * IMPORTANT: @container queries only change CHILDREN, never the container element itself.
 */
.animation-player { 
  position: relative; 
  width: 100%; 
  display: flex;
  flex-direction: column;
  background: #050505; 
  border-radius: 8px;
  container-type: inline-size;
}
.animation-player__frame { 
  width: 100%; 
  aspect-ratio: 16 / 9;
  flex-shrink: 0;
  border: 0; 
  display: block; 
}

/* Elegant Overlay for subtitles & controls — default: absolute over iframe */
.animation-player__overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 35%);
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  padding: clamp(12px, 2.5cqw, 24px);
}
.animation-player__overlay.is-hidden {
  opacity: 0;
}

/* Beautiful Subtitles */
.animation-player__subtitle-wrapper {
  transition: transform 0.4s ease;
  pointer-events: none;
}
.animation-player__overlay.is-hidden .animation-player__subtitle-wrapper {
  transform: translateY(20px);
}
.animation-player__subtitle {
  text-align: center;
  color: rgba(255, 255, 255, 0.95);
  font-size: clamp(12px, 2.2cqw, 20px);
  font-weight: 500;
  line-height: 1.5;
  margin-bottom: clamp(10px, 2cqw, 24px);
  pointer-events: auto;
  cursor: grab;
  touch-action: none;
}
.animation-player__subtitle:active {
  cursor: grabbing;
}
.animation-player__subtitle span {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: clamp(4px, 0.8cqw, 8px) clamp(10px, 1.8cqw, 18px);
  border-radius: clamp(8px, 1.2cqw, 12px);
  display: inline-block;
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

/* Modern Control Bar */
.animation-player__controls {
  display: flex;
  align-items: center;
  gap: clamp(8px, 1.5cqw, 16px);
  color: white;
  pointer-events: auto;
  transform: translateY(0);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.animation-player__overlay.is-hidden .animation-player__controls {
  transform: translateY(100%);
}

@keyframes spin { 100% { transform: rotate(360deg); } }
.icon-spin { animation: spin 1s linear infinite; }

/* Narrow layout: overlay drops BELOW the iframe (only child rules here!) */
@container (max-width: 600px) {
  .animation-player__frame {
    border-radius: 8px 8px 0 0;
  }
  .animation-player__overlay {
    position: static;
    background: #111;
    padding: 12px 16px 16px;
    flex-direction: column-reverse;
    gap: 12px;
    opacity: 1 !important;
    pointer-events: auto;
    border-radius: 0 0 8px 8px;
  }
  .animation-player__overlay.is-hidden {
    opacity: 1 !important;
  }
  .animation-player__controls {
    transform: none !important;
  }
  .animation-player__subtitle-wrapper {
    transform: none !important;
  }
  .animation-player__subtitle {
    font-size: 14px;
    margin-bottom: 0;
  }
}

.animation-player__playback { 
  flex: 1; 
  display: flex; 
  align-items: center; 
  gap: clamp(6px, 1.2cqw, 12px); 
}
.animation-player__export { 
  display: flex; 
  align-items: center; 
  gap: clamp(6px, 1cqw, 10px); 
}

/* Typography for times */
.time-text {
  font-size: clamp(11px, 1.5cqw, 13px);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: rgba(255,255,255,0.8);
  user-select: none;
}

/* Premium Icons */
.btn-icon {
  width: clamp(32px, 4cqw, 40px);
  height: clamp(32px, 4cqw, 40px);
  border: none;
  background: transparent;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-icon svg {
  width: clamp(16px, 2.5cqw, 24px);
  height: clamp(16px, 2.5cqw, 24px);
}
.btn-icon:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1.05);
}
.btn-icon:active:not(:disabled) {
  transform: scale(0.95);
}
.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-subtitle {
  opacity: 0.6;
}
.btn-subtitle.is-active {
  opacity: 1;
  color: #60a5fa;
}

/* Progress Slider */
.animation-player__progress {
  flex: 1;
  height: 5px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255,255,255,0.2);
  border-radius: 3px;
  cursor: pointer;
  transition: height 0.2s ease;
}
.animation-player__progress:hover {
  height: 8px;
}
.animation-player__progress::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
  box-shadow: 0 0 10px rgba(59,130,246,0.6);
  cursor: pointer;
  transition: transform 0.2s ease;
}
.animation-player__progress::-webkit-slider-thumb:hover {
  transform: scale(1.3);
}

/* Volume Control */
.volume-control {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(255,255,255,0.8);
}
.volume-control svg {
  width: clamp(14px, 2cqw, 18px);
  height: clamp(14px, 2cqw, 18px);
}
.volume-slider {
  width: clamp(40px, 6cqw, 60px);
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  cursor: pointer;
}
.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
}

/* Export Buttons */
.export-select {
  height: clamp(28px, 3.8cqw, 36px);
  color: white;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 8px;
  padding: 0 12px 0 8px;
  font-size: clamp(12px, 1.5cqw, 13px);
  cursor: pointer;
  outline: none;
  backdrop-filter: blur(8px);
}
.export-select option {
  background: #1e1e24;
}

.btn-export {
  height: clamp(28px, 3.8cqw, 36px);
  padding: 0 clamp(10px, 1.8cqw, 16px);
  border: none;
  background: rgba(59, 130, 246, 0.8);
  color: white;
  border-radius: 8px;
  font-size: clamp(12px, 1.5cqw, 14px);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}
.btn-export svg {
  width: clamp(14px, 1.8cqw, 16px);
  height: clamp(14px, 1.8cqw, 16px);
}
.btn-export:hover:not(:disabled) {
  background: rgba(59, 130, 246, 1);
  transform: translateY(-1px);
}
.btn-export:disabled {
  opacity: 0.5;
  background: rgba(255, 255, 255, 0.1);
  cursor: not-allowed;
}

/* Overlays / Errors */
.animation-player__notice, .animation-player__invalid, .animation-player__error { 
  position: absolute; 
  top: 16px; 
  right: 16px; 
  color: #fff; 
  background: rgba(0,0,0,.75); 
  backdrop-filter: blur(8px);
  padding: 8px 14px; 
  font-size: 13px; 
  border-radius: 8px; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.animation-player__invalid, .animation-player__error { 
  left: 16px; 
  right: auto; 
  color: #fecaca; 
  background: rgba(220, 38, 38, 0.8);
  border: 1px solid rgba(248,113,113,.4); 
}
.animation-player__error + .animation-player__error { 
  top: 60px; 
}

@media (max-width: 760px) {
  .animation-player__controls { 
    align-items: stretch; 
    flex-direction: column; 
    gap: 12px;
  }
  .animation-player__export { 
    justify-content: flex-end; 
  }
  .volume-control { 
    display: none; 
  }
}
</style>
