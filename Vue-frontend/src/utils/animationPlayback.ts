export type AudioStatus = 'ready' | 'unavailable' | 'failed'

export interface Cue {
  beatIndex: number
  startMs: number
  endMs: number
  text: string
}

export interface NarrationLike {
  version: number
  voice?: string
  audioUrl?: string
  audioStatus?: AudioStatus
  audioError?: string
  duration: number
  cues: Cue[]
}

export type PlaybackState = 'idle' | 'playing' | 'paused' | 'ended'
export type ClockMode = 'audio' | 'silent'
const MAX_CUE_DURATION_MS = 120_000

export interface SilentAnchor {
  silentStartMs: number
  silentStartPerf: number
}

export function resolveAudioStatus(narration: NarrationLike): AudioStatus {
  if (narration.audioStatus) return narration.audioStatus
  // Match podcast: any non-empty uploaded URL is treated as ready (HTTP or HTTPS).
  return narration.audioUrl ? 'ready' : 'unavailable'
}

export function shouldUseAudioClock(narration: NarrationLike, audioFailed: boolean): boolean {
  return resolveAudioStatus(narration) === 'ready' && !!narration.audioUrl && !audioFailed
}

/** Route remote Qiniu (or other) audio through the Python same-origin proxy, like image proxy. */
export function resolvePlayableAudioUrl(audioUrl: string | undefined, proxyBase: string): string | undefined {
  if (!audioUrl) return undefined
  try {
    const parsed = new URL(audioUrl)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return audioUrl
    const base = proxyBase.replace(/\/$/, '')
    return `${base}/api/ai/proxy-audio?url=${encodeURIComponent(audioUrl)}`
  } catch {
    return audioUrl
  }
}

/** Rewrite embedded podcast/animation audio URLs inside HTML to go through proxy-audio. */
export function rewriteEmbeddedAudioUrls(html: string, proxyBase: string): string {
  if (!html) return html
  return html.replace(/https?:\/\/[^\s"'\\<>]+/g, (match) => {
    if (!/\/(?:podcast-audio|animation-audio)\//i.test(match)) return match
    return resolvePlayableAudioUrl(match, proxyBase) || match
  })
}

export function findCueAtTime(cues: Cue[], currentMs: number): Cue | undefined {
  return cues.find(cue => currentMs >= cue.startMs && currentMs < cue.endMs)
}

export function narrationNotice(narration: NarrationLike, audioFailed: boolean): string | null {
  if (audioFailed) {
    return '配音加载失败，当前以字幕播放'
  }
  const status = resolveAudioStatus(narration)
  if (status === 'failed') {
    return '配音不可用，当前以字幕播放'
  }
  if (status === 'unavailable' || !narration.audioUrl) {
    return '暂无配音，当前以字幕播放'
  }
  return null
}

export function narrationIsHealthy(narration: NarrationLike | null | undefined): boolean {
  const cues = narration?.cues
  if (narration?.version !== 1 || !Array.isArray(cues) || cues.length === 0 || cues.length > 30) return false
  const code = /(?:gsap\.timeline|\.from(?:To)?\s*\(|window\.animateBeat|\b(?:const|let|var)\s+\w+\s*=)/i
  return cues.every(cue =>
    typeof cue.text === 'string'
    && cue.text.length > 0
    && cue.text.length <= 800
    && !code.test(cue.text)
    && Number.isFinite(cue.startMs)
    && Number.isFinite(cue.endMs)
    && cue.endMs > cue.startMs
    && cue.endMs - cue.startMs <= MAX_CUE_DURATION_MS,
  )
}

export function advanceSilentTime(
  silentStartMs: number,
  silentStartPerf: number,
  now: number,
  durationMs: number,
): number {
  return Math.min(durationMs, silentStartMs + (now - silentStartPerf))
}

export function createSilentAnchor(currentMs: number, now = performance.now()): SilentAnchor {
  return { silentStartMs: currentMs, silentStartPerf: now }
}

export function msFromAudioElement(audio: Pick<HTMLAudioElement, 'currentTime'> | null | undefined): number | null {
  if (!audio) return null
  const ms = Math.round(audio.currentTime * 1000)
  return Number.isFinite(ms) && ms >= 0 ? ms : null
}

export function playbackStateAfterSeek(playbackState: PlaybackState): PlaybackState {
  return playbackState === 'ended' ? 'paused' : playbackState
}

export function shouldFallbackToSilentClock(
  playbackState: PlaybackState,
  clockMode: ClockMode,
): boolean {
  return playbackState === 'playing' && clockMode === 'audio'
}

export interface PlaybackTickInput {
  playbackState: PlaybackState
  clockMode: ClockMode
  currentMs: number
  durationMs: number
  audioCurrentTimeSec: number | null
  silentAnchor: SilentAnchor
  now: number
  cues: Cue[]
  lastBeatIndex: number
}

export interface PlaybackTickResult {
  currentMs: number
  lastBeatIndex: number
  beatIndex: number
  beatChanged: boolean
  shouldEnd: boolean
}

export function computePlaybackTick(input: PlaybackTickInput): PlaybackTickResult {
  let currentMs = input.currentMs

  if (input.playbackState === 'playing') {
    if (input.clockMode === 'audio' && input.audioCurrentTimeSec !== null) {
      currentMs = input.audioCurrentTimeSec * 1000
    } else {
      currentMs = advanceSilentTime(
        input.silentAnchor.silentStartMs,
        input.silentAnchor.silentStartPerf,
        input.now,
        input.durationMs,
      )
    }
  }

  const cue = findCueAtTime(input.cues, currentMs)
  const beatIndex = cue?.beatIndex ?? -1
  const beatChanged = beatIndex >= 0 && beatIndex !== input.lastBeatIndex

  return {
    currentMs,
    lastBeatIndex: beatChanged ? beatIndex : input.lastBeatIndex,
    beatIndex,
    beatChanged,
    shouldEnd: input.playbackState === 'playing' && currentMs >= input.durationMs,
  }
}
