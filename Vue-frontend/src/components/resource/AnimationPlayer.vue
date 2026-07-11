<template>
  <div class="animation-player">
    <iframe ref="frame" class="animation-player__frame" :srcdoc="html" sandbox="allow-scripts" title="教学动画"></iframe>
    <div v-if="narrationHealthy && subtitleVisible && currentCue" class="animation-player__subtitle">{{ currentCue.text }}</div>
    <div v-if="narrationHealthy && playbackNotice" class="animation-player__notice">{{ playbackNotice }}</div>
    <div v-if="!narrationHealthy" class="animation-player__invalid">讲解数据异常，请重新生成该动画</div>
    <div v-if="bridgeError" class="animation-player__error">{{ bridgeError }}</div>
    <div v-if="exportError" class="animation-player__error">{{ exportError }}</div>
    <div class="animation-player__controls">
      <div class="animation-player__playback">
        <button type="button" :disabled="!narrationHealthy" :title="playing ? '暂停' : '播放'" @click="togglePlayback">{{ playing ? 'Ⅱ' : '▶' }}</button>
        <button type="button" title="重播" @click="replay">↻</button>
        <span>{{ formatTime(currentMs) }}</span>
        <input class="animation-player__progress" type="range" min="0" :max="durationMs" step="100" :value="currentMs" aria-label="动画进度" @input="seek">
        <span>{{ formatTime(durationMs) }}</span>
        <button type="button" :disabled="!narrationHealthy" :title="subtitleVisible ? '隐藏字幕' : '显示字幕'" @click="subtitleVisible = !subtitleVisible">字</button>
        <label title="音量"><span class="sr-only">音量</span><input type="range" min="0" max="1" step="0.05" v-model.number="volume"></label>
      </div>
      <div class="animation-player__export">
        <select v-model="selectedQuality" aria-label="导出清晰度">
        <option value="1080p">1080p</option><option value="720p">720p</option>
        </select>
        <button type="button" :disabled="!exportSupported || activeExport.status === 'rendering'" @click="handleExport">{{ exportLabel }}</button>
      </div>
    </div>
    <audio
      ref="audio"
      :src="audioSrc"
      preload="auto"
      @loadedmetadata="onAudioLoadedMetadata"
      @canplay="onAudioCanPlay"
      @error="onAudioError"
      @ended="onAudioEnded"
    ></audio>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createAnimationExport, getAnimationExports, type AnimationExportQuality, type AnimationExportState } from '@/api/resource'
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

const props = defineProps<{ resourceId: number; html: string; narration: Narration; videoExports?: Record<string, AnimationExportState> }>()
const frame = ref<HTMLIFrameElement | null>(null)
const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
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

let rafId: number | undefined
let pollTimer: number | undefined
let lastBeatIndex = -1
let silentAnchor = createSilentAnchor(0)
let clockMode: 'audio' | 'silent' = 'silent'

const durationMs = computed(() => Math.max(1, Math.round(props.narration.duration * 1000)))
const currentCue = computed(() => findCueAtTime(props.narration.cues, currentMs.value))
const audioSrc = computed(() => {
  if (!shouldUseAudioClock(props.narration, audioFailed.value)) return undefined
  return resolvePlayableAudioUrl(props.narration.audioUrl, PYTHON_AI_BASE)
})
const playbackNotice = computed(() => narrationNotice(props.narration, audioFailed.value))
const narrationHealthy = computed(() => narrationIsHealthy(props.narration))
const exportSupported = computed(() => narrationHealthy.value)
const activeExport = computed(() => exports.value[selectedQuality.value])
const exportLabel = computed(() => ({ idle: '导出视频', rendering: '生成中...', ready: '下载视频', failed: '重试导出' }[activeExport.value.status]))

// #region agent log
watch(
  () => [props.resourceId, props.narration?.audioUrl, props.narration?.audioStatus, audioSrc.value, audioFailed.value, playbackNotice.value] as const,
  ([resourceId, audioUrl, audioStatus, src, failed, notice]) => {
    fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '84be90' }, body: JSON.stringify({ sessionId: '84be90', runId: 'post-fix', hypothesisId: 'A,B,D', location: 'AnimationPlayer.vue:audioWatch', message: 'animation narration audio binding', data: { resourceId, audioUrl: audioUrl || null, audioStatus: audioStatus || null, audioSrc: src || null, usesProxy: typeof src === 'string' && src.includes('/api/ai/proxy-audio'), audioFailed: failed, notice: notice || null, duration: props.narration?.duration ?? null, cueCount: props.narration?.cues?.length ?? 0 }, timestamp: Date.now() }) }).catch(() => {})
  },
  { immediate: true },
)
// #endregion

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
  // #region agent log
  fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '84be90' }, body: JSON.stringify({ sessionId: '84be90', runId: 'post-fix', hypothesisId: 'A,D,E', location: 'AnimationPlayer.vue:startPlayback', message: 'animation startPlayback', data: { resourceId: props.resourceId, audioFailed: audioFailed.value, useAudioClock: shouldUseAudioClock(props.narration, audioFailed.value), audioSrc: audioSrc.value || null, mediaReadyState: audio.value?.readyState ?? null, mediaNetworkState: audio.value?.networkState ?? null, mediaError: audio.value?.error?.code ?? null, currentMs: currentMs.value }, timestamp: Date.now() }) }).catch(() => {})
  // #endregion
  if (currentMs.value >= durationMs.value) {
    currentMs.value = 0
    lastBeatIndex = -1
    silentAnchor = createSilentAnchor(0)
    if (audio.value && Number.isFinite(audio.value.duration)) audio.value.currentTime = 0
  }

  playbackState.value = 'playing'
  playing.value = true

  if (shouldUseAudioClock(props.narration, audioFailed.value) && audio.value) {
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
      // #region agent log
      fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '84be90' }, body: JSON.stringify({ sessionId: '84be90', runId: 'post-fix', hypothesisId: 'A,E', location: 'AnimationPlayer.vue:playCatch', message: 'animation audio.play rejected', data: { name: err instanceof Error ? err.name : 'unknown', message: err instanceof Error ? err.message : String(err), mediaError: audio.value?.error?.code ?? null }, timestamp: Date.now() }) }).catch(() => {})
      // #endregion
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

  if (audio.value && clockMode === 'audio' && shouldUseAudioClock(props.narration, audioFailed.value)) {
    audio.value.currentTime = nextMs / 1000
  }

  const cue = findCueAtTime(props.narration.cues, nextMs)
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
  // #region agent log
  fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '84be90' }, body: JSON.stringify({ sessionId: '84be90', runId: 'post-fix', hypothesisId: 'A,B,D', location: 'AnimationPlayer.vue:onAudioError', message: 'animation audio element error', data: { resourceId: props.resourceId, src: audio.value?.currentSrc || audioSrc.value || null, code: audio.value?.error?.code ?? null, mediaNetworkState: audio.value?.networkState ?? null }, timestamp: Date.now() }) }).catch(() => {})
  // #endregion
  audioFailed.value = true
  if (playbackState.value === 'playing' && clockMode === 'audio') {
    startSilentClock()
  }
}

function onAudioEnded() {
  endPlayback()
}

async function refreshExports() {
  const result = await getAnimationExports(props.resourceId)
  exports.value = result.qualities
  // #region agent log
  const snap = Object.fromEntries(Object.entries(result.qualities || {}).map(([k, v]) => [k, { status: v.status, error: v.error || null, hasUrl: !!v.url }]))
  fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'55a441'},body:JSON.stringify({sessionId:'55a441',runId:'pre-fix',hypothesisId:'A,B,C,E,F',location:'AnimationPlayer.vue:refreshExports',message:'export poll',data:{resourceId:props.resourceId,qualities:snap},timestamp:Date.now()})}).catch(()=>{})
  // #endregion
  const active = exports.value[selectedQuality.value]
  if (active?.status === 'failed' && active.error) exportError.value = active.error
  if (Object.values(exports.value).some(state => state.status === 'rendering')) pollTimer = window.setTimeout(refreshExports, 2000)
}

async function handleExport() {
  exportError.value = ''
  if (!exportSupported.value) { exportError.value = '当前动画的讲解数据已损坏，请重新生成后导出'; return }
  const state = activeExport.value
  if (state.status === 'ready' && state.url) { window.open(state.url, '_blank'); return }
  try {
    // #region agent log
    fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'55a441'},body:JSON.stringify({sessionId:'55a441',runId:'pre-fix',hypothesisId:'A,D',location:'AnimationPlayer.vue:handleExport',message:'export click',data:{resourceId:props.resourceId,quality:selectedQuality.value,priorStatus:state.status,priorError:state.error||null,narrationHealthy:narrationHealthy.value},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
    const result = await createAnimationExport(props.resourceId, selectedQuality.value)
    exports.value = result.qualities
    // #region agent log
    fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'55a441'},body:JSON.stringify({sessionId:'55a441',runId:'pre-fix',hypothesisId:'A,F',location:'AnimationPlayer.vue:handleExport:ok',message:'export api accepted',data:{resourceId:props.resourceId,accepted:result.accepted,qualities:Object.fromEntries(Object.entries(result.qualities||{}).map(([k,v])=>[k,{status:v.status,error:v.error||null,hasUrl:!!v.url}]))},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
    const failed = result.qualities?.[selectedQuality.value]
    if (failed?.status === 'failed' && failed.error) exportError.value = failed.error
    window.clearTimeout(pollTimer); pollTimer = window.setTimeout(refreshExports, 1500)
  } catch (error) {
    // #region agent log
    fetch('http://127.0.0.1:7296/ingest/e9514b2d-72ba-413a-b7bd-0ae318ec510a',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'55a441'},body:JSON.stringify({sessionId:'55a441',runId:'pre-fix',hypothesisId:'A,D',location:'AnimationPlayer.vue:handleExport:err',message:'export api error',data:{resourceId:props.resourceId,error:error instanceof Error?error.message:String(error)},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
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
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onFrameMessage)
  cleanupClock()
  window.clearTimeout(pollTimer)
})
</script>

<style scoped>
.animation-player { position: relative; width: 100%; aspect-ratio: 16 / 9; overflow: hidden; background: #050505; }
.animation-player__frame { width: 100%; height: 100%; border: 0; display: block; }
.animation-player__subtitle { position: absolute; left: 8%; right: 8%; bottom: 74px; text-align: center; color: white; font-size: 18px; font-weight: 600; line-height: 1.55; text-shadow: 0 2px 5px #000; pointer-events: none; }
.animation-player__notice,.animation-player__invalid,.animation-player__error { position: absolute; top: 12px; right: 12px; color: #fff; background: rgba(0,0,0,.72); padding: 7px 10px; font-size: 12px; border-radius: 4px; }
.animation-player__invalid,.animation-player__error { left: 12px; right: auto; color: #fecaca; border: 1px solid rgba(248,113,113,.4); }
.animation-player__error + .animation-player__error { top: 48px; }
.animation-player__controls { position: absolute; left: 12px; right: 12px; bottom: 12px; min-height: 46px; display: flex; align-items: center; gap: 8px; padding: 6px 8px; color: white; background: rgba(7,8,10,.86); border: 1px solid rgba(255,255,255,.16); border-radius: 7px; }
.animation-player__playback { min-width: 0; flex: 1; display: flex; align-items: center; gap: 8px; }
.animation-player__export { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
.animation-player__controls button { min-width: 34px; height: 32px; border: 0; color: white; background: rgba(255,255,255,.12); border-radius: 5px; padding: 0 9px; }
.animation-player__controls button:disabled { opacity: .55; }
.animation-player__controls select { height: 32px; color: white; background: #25272b; border: 1px solid #555; border-radius: 4px; }
.animation-player__progress { flex: 1; min-width: 80px; }
.animation-player__controls label input { width: 72px; }
@media (max-width: 760px) {
  .animation-player__controls { align-items: stretch; flex-direction: column; }
  .animation-player__export { justify-content: flex-end; }
  .animation-player__controls label { display: none; }
  .animation-player__subtitle { bottom: 96px; font-size: 14px; }
}
</style>
