import { expect, test } from '@playwright/test'
import { getLegacyBridgeScriptSource, prepareAnimationHtmlForPlayer } from '../src/utils/animationHtml'

const GSAP = 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js'

function buildFixtureHtml(bridgeScript: string, options: { stripWaapi?: boolean } = {}) {
  const waapiStub = options.stripWaapi
    ? `<script>document.getAnimations = undefined; Element.prototype.getAnimations = undefined;</script>`
    : ''
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <script src="${GSAP}"></script>
  ${waapiStub}
  ${bridgeScript}
  <style>
    html, body { margin: 0; background: #050505; width: 100%; height: 100%; }
    .beat { position: absolute; inset: 40px; display: none; }
    .beat.active { display: block; }
    .title { font-size: 28px; color: #fff; opacity: 0; }
    .card { width: 220px; height: 120px; margin-top: 24px; background: #38bdf8; opacity: 0; border-radius: 12px; }
    .card.alt { background: #f97316; }
  </style>
</head>
<body>
  <section class="beat active" data-beat="0">
    <div class="title" id="title0">第一幕标题</div>
    <div class="card" id="card0">卡片</div>
  </section>
  <section class="beat" data-beat="1">
    <div class="title" id="title1">第二幕标题</div>
    <div class="card alt" id="card1">卡片</div>
  </section>
  <script>
    window.animateBeat = function(index) {
      const title = index === 0 ? '#title0' : '#title1';
      const card = index === 0 ? '#card0' : '#card1';
      return gsap.timeline()
        .from(title, { opacity: 0, y: 20, duration: 0.5, ease: 'power2.out' })
        .from(card, { opacity: 0, y: 24, duration: 0.5, ease: 'power2.out' }, '-=0.2');
    };
  </script>
</body>
</html>`
}

function buildStageFitFixture() {
  const raw = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <script src="${GSAP}"></script>
  <style>
    body { margin: 0; display: grid; place-items: center; min-height: 100vh; background: #050505; overflow: hidden; }
    #stage { position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #111; }
    .beat { position: absolute; inset: 0; display: none; }
    .beat.active { display: block; }
    .title { position: absolute; left: 120px; top: 180px; font-size: 64px; color: #fff; }
    .card-row { position: absolute; left: 120px; right: 120px; top: 420px; display: flex; gap: 40px; }
    .card { flex: 1; height: 280px; background: #38bdf8; border-radius: 24px; }
  </style>
</head>
<body>
  <main id="stage">
    <section class="beat active" data-beat="0">
      <div class="title">String 操作</div>
      <div class="card-row"><div class="card"></div><div class="card"></div><div class="card" id="right-card"></div></div>
    </section>
  </main>
  <script>
    window.animateBeat = function() {
      return gsap.timeline().from('.title, .card', { opacity: 0, duration: 0.01 });
    };
  </script>
</body>
</html>`
  return prepareAnimationHtmlForPlayer(raw)
}

async function waitForBridge(page: import('@playwright/test').Page) {
  await page.waitForFunction(() => (window as typeof window & { __AURA_BRIDGE?: unknown }).__AURA_BRIDGE)
}

async function opacityOf(page: import('@playwright/test').Page, selector: string) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel) as HTMLElement | null
    return el ? Number.parseFloat(getComputedStyle(el).opacity || '0') : 0
  }, selector)
}

test.describe('animation bridge preview', () => {
  test('idle preview is completed and non-black; play animates opacity 0→1', async ({ page }) => {
    const bridge = getLegacyBridgeScriptSource()
    await page.setContent(buildFixtureHtml(bridge), { waitUntil: 'networkidle' })
    await waitForBridge(page)

    const idle = await page.evaluate(() => {
      const title = document.querySelector('#title0') as HTMLElement
      const card = document.querySelector('#card0') as HTMLElement
      return {
        active: document.querySelector('.beat.active')?.getAttribute('data-beat'),
        titleOpacity: Number.parseFloat(getComputedStyle(title).opacity || '0'),
        cardOpacity: Number.parseFloat(getComputedStyle(card).opacity || '0'),
        globalPaused: (window as typeof window & { gsap: { globalTimeline: { paused: () => boolean } } }).gsap.globalTimeline.paused(),
        ready: true,
      }
    })

    expect(idle.active).toBe('0')
    expect(idle.titleOpacity).toBeGreaterThan(0.9)
    expect(idle.cardOpacity).toBeGreaterThan(0.9)
    expect(idle.globalPaused).toBe(true)

    await page.evaluate(() => {
      (window as typeof window & { __AURA_BRIDGE: { play: () => void } }).__AURA_BRIDGE.play()
    })

    await page.waitForFunction(() => {
      const card = document.querySelector('#card0') as HTMLElement
      const opacity = Number.parseFloat(getComputedStyle(card).opacity || '0')
      const gsap = (window as typeof window & { gsap: { globalTimeline: { paused: () => boolean } } }).gsap
      return !gsap.globalTimeline.paused() && opacity < 0.95
    }, undefined, { timeout: 2000 })

    await page.waitForFunction(() => {
      const card = document.querySelector('#card0') as HTMLElement
      return Number.parseFloat(getComputedStyle(card).opacity || '0') > 0.9
    }, undefined, { timeout: 3000 })

    expect(await opacityOf(page, '#card0')).toBeGreaterThan(0.9)
  })

  test('cross-cue beat switch shows visible content within one second', async ({ page }) => {
    const bridge = getLegacyBridgeScriptSource()
    await page.setContent(buildFixtureHtml(bridge), { waitUntil: 'networkidle' })
    await waitForBridge(page)

    await page.evaluate(() => {
      (window as typeof window & { __AURA_BRIDGE: { play: () => void } }).__AURA_BRIDGE.play()
    })
    await page.waitForTimeout(200)
    await page.evaluate(() => {
      parent.postMessage({ type: '__AURA_LEGACY_CONTROL__', action: 'beat', beatIndex: 1 }, '*')
      // Direct bridge call mirrors AnimationPlayer beat control
      ;(window as typeof window & { __AURA_BRIDGE: { enterBeat: (i: number, o?: object) => void } })
        .__AURA_BRIDGE.enterBeat(1, { play: true })
    })

    await page.waitForFunction(() => {
      const active = document.querySelector('.beat.active')
      const card = document.querySelector('#card1') as HTMLElement
      return active?.getAttribute('data-beat') === '1'
        && Number.parseFloat(getComputedStyle(card).opacity || '0') > 0.5
    }, undefined, { timeout: 1000 })

    expect(await opacityOf(page, '#card1')).toBeGreaterThan(0.5)
  })

  test('pause/resume/seek/replay do not leave a transparent beat', async ({ page }) => {
    const bridge = getLegacyBridgeScriptSource()
    await page.setContent(buildFixtureHtml(bridge), { waitUntil: 'networkidle' })
    await waitForBridge(page)
    const api = () => (window as typeof window & {
      __AURA_BRIDGE: {
        play: () => void
        pause: () => void
        replay: () => void
        enterBeat: (i: number, o?: object) => void
      }
    }).__AURA_BRIDGE

    await page.evaluate(() => api().play())
    await page.waitForTimeout(150)
    await page.evaluate(() => api().pause())
    expect(await opacityOf(page, '#card0')).toBeGreaterThan(0)

    await page.evaluate(() => {
      parent.postMessage({ type: '__AURA_LEGACY_CONTROL__', action: 'seek', beatIndex: 1 }, '*')
      // paused seek uses preview path via message; call enterBeat preview directly for reliability
      ;(window as typeof window & { __AURA_BRIDGE: { enterBeat: (i: number, o?: object) => void } })
        .__AURA_BRIDGE.enterBeat(1, { preview: true })
    })
    await page.waitForTimeout(50)
    expect(await opacityOf(page, '#card1')).toBeGreaterThan(0.9)

    await page.evaluate(() => api().replay())
    await page.waitForFunction(() => {
      const gsap = (window as typeof window & { gsap: { globalTimeline: { paused: () => boolean } } }).gsap
      return !gsap.globalTimeline.paused()
    })
    await page.waitForFunction(() => {
      const card = document.querySelector('#card1') as HTMLElement
      return Number.parseFloat(getComputedStyle(card).opacity || '0') > 0.9
    }, undefined, { timeout: 3000 })
  })

  test('works without Web Animations API', async ({ page }) => {
    const bridge = getLegacyBridgeScriptSource()
    await page.setContent(buildFixtureHtml(bridge, { stripWaapi: true }), { waitUntil: 'networkidle' })
    await waitForBridge(page)

    expect(await opacityOf(page, '#card0')).toBeGreaterThan(0.9)
    await page.evaluate(() => {
      (window as typeof window & { __AURA_BRIDGE: { play: () => void } }).__AURA_BRIDGE.play()
    })
    await page.waitForFunction(() => {
      const gsap = (window as typeof window & { gsap: { globalTimeline: { paused: () => boolean } } }).gsap
      return !gsap.globalTimeline.paused()
    })
    await page.waitForFunction(() => {
      const card = document.querySelector('#card0') as HTMLElement
      return Number.parseFloat(getComputedStyle(card).opacity || '0') > 0.9
    }, undefined, { timeout: 3000 })
  })

  test('animateBeat failure still shows first beat via fallback', async ({ page }) => {
    const bridge = getLegacyBridgeScriptSource()
    const html = buildFixtureHtml(bridge).replace(
      'window.animateBeat = function(index) {',
      'window.animateBeat = function(index) { throw new Error("broken");',
    )
    await page.setContent(html, { waitUntil: 'networkidle' })
    await waitForBridge(page)

    const visible = await page.evaluate(() => {
      const beat = document.querySelector('.beat.active') as HTMLElement | null
      if (!beat) return false
      const style = getComputedStyle(beat)
      return style.display !== 'none' && style.visibility !== 'hidden'
    })
    expect(visible).toBe(true)
  })

  test('ready message reports bridgeReady and gsapReady', async ({ page }) => {
    await page.addInitScript(() => {
      ;(window as typeof window & { __readyMessages?: unknown[] }).__readyMessages = []
      window.addEventListener('message', (event) => {
        const message = event.data
        if (message && message.type === '__AURA_LEGACY_READY__') {
          ;(window as typeof window & { __readyMessages: unknown[] }).__readyMessages.push(message)
        }
      })
    })
    const bridge = getLegacyBridgeScriptSource()
    await page.setContent(buildFixtureHtml(bridge), { waitUntil: 'networkidle' })
    await waitForBridge(page)
    const ready = await page.waitForFunction(() => {
      const messages = (window as typeof window & { __readyMessages?: Array<{ bridgeReady?: boolean; gsapReady?: boolean }> }).__readyMessages
      return messages && messages.length ? messages[messages.length - 1] : null
    })
    const payload = await ready.jsonValue() as { bridgeReady: boolean; gsapReady: boolean }
    expect(payload.bridgeReady).toBe(true)
    expect(payload.gsapReady).toBe(true)
  })

  test('narrow viewport keeps full 1920 stage centered without mid-stage crop', async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 506 })
    await page.setContent(buildStageFitFixture(), { waitUntil: 'networkidle' })
    await waitForBridge(page)
    await page.waitForFunction(() => {
      const stage = document.getElementById('stage')
      return !!stage && stage.style.transform.includes('scale(')
    })

    const layout = await page.evaluate(() => {
      const stage = document.getElementById('stage') as HTMLElement
      const rightCard = document.getElementById('right-card') as HTMLElement
      const stageRect = stage.getBoundingClientRect()
      const cardRect = rightCard.getBoundingClientRect()
      const scale = Number.parseFloat((stage.style.transform.match(/scale\(([^)]+)\)/) || [])[1] || '0')
      return {
        scale,
        stageLeft: stageRect.left,
        stageRight: stageRect.right,
        stageWidth: stageRect.width,
        viewportWidth: window.innerWidth,
        cardRight: cardRect.right,
        cardVisible: cardRect.right <= window.innerWidth + 1 && cardRect.left >= -1,
      }
    })

    expect(layout.scale).toBeGreaterThan(0)
    expect(layout.scale).toBeLessThanOrEqual(1)
    expect(layout.stageWidth).toBeLessThanOrEqual(layout.viewportWidth + 1)
    expect(Math.abs(layout.stageLeft - (layout.viewportWidth - layout.stageWidth) / 2)).toBeLessThan(2)
    expect(layout.cardVisible).toBe(true)
    expect(layout.cardRight).toBeLessThanOrEqual(layout.viewportWidth + 1)
  })
})
