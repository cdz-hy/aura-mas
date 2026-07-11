import { describe, expect, it } from 'vitest'
import {
  bridgeExposesAuraBridge,
  bridgeFreezesOnInit,
  bridgePausesBeatAndGlobalTimeline,
  bridgeResumesGlobalTimelineBeforeBeatPlay,
  bridgeRestartsFromPreviewOnPlay,
  bridgeUsesAnimateBeatContract,
  bridgeUsesPreviewMode,
  bridgeUsesWaapiCapabilityGuards,
  getLegacyBridgeScriptSource,
  hasNakedAnimationScript,
  playerHtmlScalesStageToViewport,
  prepareAnimationHtmlForPlayer,
  repairDanglingAnimationScript,
} from './animationHtml'

describe('animation HTML repair', () => {
  it('moves a pure JavaScript tail back into the preceding script', () => {
    const broken = '<html><body><div class="beat active">画面</div><script>const first = 1;</script>window.animateBeat6=function(){var tl=gsap.timeline();};</body></html>'
    const repaired = repairDanglingAnimationScript(broken)
    expect(repaired).toContain('const first = 1;\nwindow.animateBeat6')
    expect(hasNakedAnimationScript(repaired)).toBe(false)
  })

  it('does not move normal HTML after a script', () => {
    const html = '<html><body><script>const ok=1;</script><footer>说明</footer></body></html>'
    expect(repairDanglingAnimationScript(html)).toBe(html)
  })
})

describe('animation bridge', () => {
  it('injects animateBeat contract, preview mode, and init freeze logic', () => {
    const bridge = getLegacyBridgeScriptSource()
    expect(bridgeUsesAnimateBeatContract(bridge)).toBe(true)
    expect(bridgeFreezesOnInit(bridge)).toBe(true)
    expect(bridgeUsesPreviewMode(bridge)).toBe(true)
    expect(bridgeRestartsFromPreviewOnPlay(bridge)).toBe(true)
    expect(bridgeExposesAuraBridge(bridge)).toBe(true)
  })

  it('resumes global timeline before recreating the beat timeline on play', () => {
    const bridge = getLegacyBridgeScriptSource()
    expect(bridgeResumesGlobalTimelineBeforeBeatPlay(bridge)).toBe(true)
    expect(bridgePausesBeatAndGlobalTimeline(bridge)).toBe(true)
    expect(bridgeUsesWaapiCapabilityGuards(bridge)).toBe(true)
  })

  it('prepares player html with bridge and stage viewport fit', () => {
    const html = prepareAnimationHtmlForPlayer(
      '<html><head></head><body><div id="stage"><div class="beat active">A</div></div></body></html>',
    )
    expect(html).toContain('__AURA_LEGACY_CONTROL__')
    expect(html).toContain('window.__AURA_BRIDGE')
    expect(html).toContain('freezeAllAnimations')
    expect(html).toContain('resumeGlobalTimeline')
    expect(html).toContain('bridgeReady')
    expect(playerHtmlScalesStageToViewport(html)).toBe(true)
    expect(html).toContain('aura-stage-fit-style')
    expect(html.indexOf('aura-stage-fit-style')).toBeLessThan(html.indexOf('id="aura-stage-fit"'))
  })

  it('scales 1920x1080 stage so it fits a narrow iframe viewport without clipping to mid-stage', () => {
    const html = prepareAnimationHtmlForPlayer(
      '<html><head></head><body><main id="stage" style="width:1920px;height:1080px"><section class="beat active">画面</section></main></body></html>',
    )
    expect(html).toContain('Math.min(vw / STAGE_W, vh / STAGE_H)')
    expect(html).toContain('Math.max(0, (vw - STAGE_W * scale) / 2)')
    expect(html).toContain('Math.max(0, (vh - STAGE_H * scale) / 2)')
    expect(html).toContain('body{display:block!important;place-items:unset!important')
  })
})
