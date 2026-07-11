import { describe, expect, it } from 'vitest'
import {
  advanceSilentTime,
  computePlaybackTick,
  createSilentAnchor,
  findCueAtTime,
  narrationNotice,
  narrationIsHealthy,
  resolveAudioStatus,
  resolvePlayableAudioUrl,
  rewriteEmbeddedAudioUrls,
  shouldUseAudioClock,
} from './animationPlayback'

const cues = [
  { beatIndex: 0, startMs: 0, endMs: 2000, text: '第一段' },
  { beatIndex: 1, startMs: 2000, endMs: 5000, text: '第二段' },
]

describe('animationPlayback', () => {
  it('resolves legacy narration without audioStatus', () => {
    expect(resolveAudioStatus({ version: 1, duration: 5, cues, audioUrl: 'https://audio.test/a.wav' })).toBe('ready')
    expect(resolveAudioStatus({ version: 1, duration: 5, cues, audioUrl: 'http://audio.test/a.wav' })).toBe('ready')
    expect(resolveAudioStatus({ version: 1, duration: 5, cues, audioUrl: '' })).toBe('unavailable')
  })

  it('uses audio clock only when ready and not failed', () => {
    const ready = { version: 1, duration: 5, cues, audioUrl: 'https://audio.test/a.wav', audioStatus: 'ready' as const }
    expect(shouldUseAudioClock(ready, false)).toBe(true)
    expect(shouldUseAudioClock(ready, true)).toBe(false)
    expect(shouldUseAudioClock({ ...ready, audioStatus: 'failed' }, false)).toBe(false)
    expect(shouldUseAudioClock({ ...ready, audioUrl: '' }, false)).toBe(false)
    expect(shouldUseAudioClock({ version: 1, duration: 5, cues, audioUrl: 'http://audio.test/a.wav' }, false)).toBe(true)
  })

  it('finds cue by current time', () => {
    expect(findCueAtTime(cues, 500)?.beatIndex).toBe(0)
    expect(findCueAtTime(cues, 2500)?.beatIndex).toBe(1)
    expect(findCueAtTime(cues, 5000)).toBeUndefined()
  })

  it('advances silent clock with performance anchor', () => {
    const anchor = createSilentAnchor(1000, 1000)
    expect(advanceSilentTime(anchor.silentStartMs, anchor.silentStartPerf, 2500, 10000)).toBe(2500)
    expect(advanceSilentTime(anchor.silentStartMs, anchor.silentStartPerf, 12000, 5000)).toBe(5000)
  })

  it('shows distinct notices for unavailable and failed narration', () => {
    expect(narrationNotice({ version: 1, duration: 5, cues, audioUrl: '' }, false)).toBe('暂无配音，当前以字幕播放')
    expect(narrationNotice({ version: 1, duration: 5, cues, audioStatus: 'failed' }, false)).toBe('配音不可用，当前以字幕播放')
    expect(narrationNotice({ version: 1, duration: 5, cues, audioUrl: 'http://audio.test/a.wav' }, false)).toBeNull()
    expect(narrationNotice({ version: 1, duration: 5, cues, audioUrl: 'https://audio.test/a.wav', audioStatus: 'ready' }, true)).toBe('配音加载失败，当前以字幕播放')
    expect(narrationNotice({ version: 1, duration: 5, cues, audioUrl: 'https://audio.test/a.wav', audioStatus: 'ready' }, false)).toBeNull()
  })

  it('resolves remote audio through the AI proxy', () => {
    expect(resolvePlayableAudioUrl(undefined, 'http://localhost:8002')).toBeUndefined()
    expect(resolvePlayableAudioUrl('http://cdn.test/a.wav', 'http://localhost:8002')).toBe(
      'http://localhost:8002/api/ai/proxy-audio?url=' + encodeURIComponent('http://cdn.test/a.wav'),
    )
    expect(resolvePlayableAudioUrl('blob:http://localhost/x', 'http://localhost:8002')).toBe('blob:http://localhost/x')
  })

  it('rewrites embedded podcast/animation audio urls through proxy', () => {
    const html = 'const audioUrl = "http://old.example/podcast-audio/a.wav";'
    expect(rewriteEmbeddedAudioUrls(html, 'http://localhost:8002')).toContain('/api/ai/proxy-audio?url=')
    expect(rewriteEmbeddedAudioUrls('no audio here', 'http://localhost:8002')).toBe('no audio here')
  })

  it('accepts a spoken beat longer than 30 seconds', () => {
    expect(narrationIsHealthy({
      version: 1,
      duration: 31,
      audioUrl: 'https://audio.test/a.wav',
      cues: [{ beatIndex: 0, startMs: 0, endMs: 31_000, text: '较长的自然中文讲解' }],
    })).toBe(true)
  })
})

describe('computePlaybackTick', () => {
  const durationMs = 5000
  const baseInput = {
    playbackState: 'playing' as const,
    clockMode: 'audio' as const,
    currentMs: 0,
    durationMs,
    audioCurrentTimeSec: null as number | null,
    silentAnchor: createSilentAnchor(0, 0),
    now: 0,
    cues,
    lastBeatIndex: -1,
  }

  it('advances time from audio clock', () => {
    const result = computePlaybackTick({ ...baseInput, audioCurrentTimeSec: 1.5 })
    expect(result.currentMs).toBe(1500)
    expect(result.beatIndex).toBe(0)
    expect(result.beatChanged).toBe(true)
    expect(result.shouldEnd).toBe(false)
  })

  it('advances time from silent clock', () => {
    const result = computePlaybackTick({
      ...baseInput,
      clockMode: 'silent',
      silentAnchor: createSilentAnchor(0, 0),
      now: 3000,
    })
    expect(result.currentMs).toBe(3000)
    expect(result.beatIndex).toBe(1)
    expect(result.beatChanged).toBe(true)
  })

  it('does not advance when paused', () => {
    const result = computePlaybackTick({ ...baseInput, playbackState: 'paused', currentMs: 1500 })
    expect(result.currentMs).toBe(1500)
  })

  it('detects beat change and updates lastBeatIndex', () => {
    const result = computePlaybackTick({ ...baseInput, audioCurrentTimeSec: 2.5, lastBeatIndex: 0 })
    expect(result.beatIndex).toBe(1)
    expect(result.beatChanged).toBe(true)
    expect(result.lastBeatIndex).toBe(1)
  })

  it('does not flag beat change for same beat', () => {
    const result = computePlaybackTick({ ...baseInput, audioCurrentTimeSec: 0.5, lastBeatIndex: 0 })
    expect(result.beatIndex).toBe(0)
    expect(result.beatChanged).toBe(false)
    expect(result.lastBeatIndex).toBe(0)
  })

  it('signals end when currentMs reaches duration', () => {
    const result = computePlaybackTick({ ...baseInput, audioCurrentTimeSec: 5 })
    expect(result.shouldEnd).toBe(true)
  })

  it('clamps silent clock to duration', () => {
    const result = computePlaybackTick({
      ...baseInput,
      clockMode: 'silent',
      silentAnchor: createSilentAnchor(0, 0),
      now: 99999,
    })
    expect(result.currentMs).toBe(durationMs)
  })
})
