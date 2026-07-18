const LEGACY_CONTROL_TYPE = '__AURA_LEGACY_CONTROL__'
const LEGACY_PROGRESS_TYPE = '__AURA_LEGACY_PROGRESS__'
const LEGACY_READY_TYPE = '__AURA_LEGACY_READY__'

export const ANIMATION_CONTROL_TYPE = LEGACY_CONTROL_TYPE

function buildLegacyBridgeScript() {
  const closeScript = '<' + '/script>'
  return `<script>
(() => {
  const CONTROL = "${LEGACY_CONTROL_TYPE}";
  const PROGRESS = "${LEGACY_PROGRESS_TYPE}";
  const READY = "${LEGACY_READY_TYPE}";
  const ALLOWED_ACTIONS = new Set(["play", "pause", "prev", "next", "replay", "seek", "beat", "progress"]);
  const nativeSetInterval = window.setInterval.bind(window);
  window.__AURA_LEGACY_PAUSED = true;
  let currentBeatIndex = -1;
  let currentBeatAnimation = null;
  let previewMode = true;
  window.setInterval = (fn, delay, ...args) => nativeSetInterval(() => {
    if (!window.__AURA_LEGACY_PAUSED) fn(...args);
  }, delay);

  function isControlMessage(message) {
    return !!message
      && typeof message === "object"
      && message.type === CONTROL
      && ALLOWED_ACTIONS.has(message.action)
      && (message.action !== "pause" || typeof message.paused === "boolean")
      && (message.action !== "beat" || Number.isInteger(message.beatIndex));
  }

  function beats() {
    return [...document.querySelectorAll(".beat")];
  }

  function activeIndex() {
    const items = beats();
    const index = items.findIndex(beat => beat.classList.contains("active"));
    return { beats: items, index: Math.max(0, index) };
  }

  function gsapReady() {
    return typeof gsap !== "undefined";
  }

  function getDocumentAnimations() {
    if (typeof document.getAnimations !== "function") return [];
    try { return document.getAnimations({ subtree: true }); } catch (e) { return []; }
  }

  function getElementAnimations(element) {
    if (!element || typeof element.getAnimations !== "function") return [];
    try { return element.getAnimations({ subtree: true }); } catch (e) { return []; }
  }

  function pauseCssAnimations() {
    getDocumentAnimations().forEach(animation => {
      try { animation.pause(); } catch (e) {}
    });
  }

  function playCssAnimations() {
    getDocumentAnimations().forEach(animation => {
      try { animation.play(); } catch (e) {}
    });
  }

  function resumeGlobalTimeline() {
    if (!gsapReady()) return;
    try { gsap.globalTimeline.play(); } catch (e) {}
  }

  function pauseGlobalTimeline() {
    if (!gsapReady()) return;
    try { gsap.globalTimeline.pause(); } catch (e) {}
  }

  function postProgress(type = PROGRESS, extra = {}) {
    const state = activeIndex();
    parent.postMessage({
      type,
      total: state.beats.length,
      index: state.beats.length ? state.index + 1 : 0,
      bridgeReady: true,
      gsapReady: gsapReady(),
      ...extra,
    }, "*");
  }

  function freezeAllAnimations() {
    pauseCssAnimations();
    pauseGlobalTimeline();
  }

  function setBeatVisibility(nextIndex) {
    const state = activeIndex();
    if (!state.beats.length) return false;
    const normalized = ((nextIndex % state.beats.length) + state.beats.length) % state.beats.length;
    state.beats.forEach((beat, index) => {
      const isActive = index === normalized;
      beat.classList.toggle("active", isActive);
      if (isActive) {
        beat.style.opacity = "1";
        beat.style.visibility = "visible";
        beat.style.removeProperty("display");
      } else {
        beat.style.display = "none";
        beat.style.removeProperty("opacity");
        beat.style.removeProperty("visibility");
      }
    });
    return normalized;
  }

  function previewAnimationsFallback() {
    const active = document.querySelector(".beat.active") || document.body;
    if (gsapReady() && active) {
      try {
        gsap.set(active, { opacity: 1, visibility: "visible" });
        gsap.set(active.querySelectorAll("*"), { opacity: 1, y: 0, x: 0, scale: 1 });
      } catch (e) {}
    }
  }

  function replayAnimationsFallback() {
    const active = document.querySelector(".beat.active") || document.body;
    getElementAnimations(active).forEach(animation => {
      try {
        animation.cancel();
        animation.play();
      } catch (e) {}
    });
    if (!gsapReady()) return;
    try {
      const activeElements = new Set(active?.querySelectorAll("*") || []);
      if (active) activeElements.add(active);
      let foundCustomAnimation = false;
      const allAnimations = gsap.globalTimeline.getChildren(false, true, true);
      allAnimations.forEach(anim => {
        let targets = [];
        if (typeof anim.targets === "function") targets = anim.targets();
        else if (anim.getChildren) {
          anim.getChildren(true, true, false).forEach(t => {
            if (typeof t.targets === "function") targets.push(...t.targets());
          });
        }
        if (targets.some(target => activeElements.has(target))) {
          anim.restart();
          foundCustomAnimation = true;
        }
      });
      if (!foundCustomAnimation) {
        gsap.killTweensOf(active?.querySelectorAll("*"));
        const children = active?.querySelectorAll("[class]");
        if (children && children.length) {
          gsap.fromTo(
            [...children],
            { opacity: 0, y: 30 },
            { opacity: 1, y: 0, duration: 0.6, stagger: 0.08, ease: "power2.out", overwrite: true }
          );
        }
      }
    } catch (e) {}
  }

  function finishTimelinePreview(timeline) {
    if (!timeline) return;
    try {
      if (typeof timeline.progress === "function") {
        timeline.progress(1);
      } else if (typeof timeline.time === "function") {
        const duration = typeof timeline.totalDuration === "function"
          ? timeline.totalDuration()
          : (typeof timeline.duration === "function" ? timeline.duration() : 0);
        timeline.time(Math.max(0, duration));
      }
      if (typeof timeline.pause === "function") timeline.pause();
    } catch (e) {}
  }

  function killCurrentBeatAnimation() {
    if (currentBeatAnimation && typeof currentBeatAnimation.kill === "function") {
      try { currentBeatAnimation.kill(); } catch (e) {}
    }
    currentBeatAnimation = null;
  }

  function invokeAnimateBeat(index, mode) {
    killCurrentBeatAnimation();
    if (typeof window.animateBeat === "function") {
      try {
        if (mode === "play") {
          resumeGlobalTimeline();
        }
        currentBeatAnimation = window.animateBeat(index) || null;
        if (currentBeatAnimation) {
          if (mode === "preview") {
            finishTimelinePreview(currentBeatAnimation);
          } else if (mode === "play") {
            if (typeof currentBeatAnimation.restart === "function") {
              currentBeatAnimation.restart(true);
            } else if (typeof currentBeatAnimation.play === "function") {
              currentBeatAnimation.play();
            }
            playCssAnimations();
          }
          return true;
        }
      } catch (e) {
        currentBeatAnimation = null;
      }
    }
    if (mode === "preview") requestAnimationFrame(previewAnimationsFallback);
    else {
      resumeGlobalTimeline();
      requestAnimationFrame(replayAnimationsFallback);
    }
    return false;
  }

  function enterBeat(nextIndex, options = {}) {
    const preview = !!options.preview;
    const play = !!options.play || !!options.replay;
    const normalized = setBeatVisibility(nextIndex);
    if (normalized === false) return false;
    const beatChanged = normalized !== currentBeatIndex;
    const shouldUpdate = preview || play || beatChanged;
    if (!shouldUpdate) {
      postProgress();
      return true;
    }
    currentBeatIndex = normalized;
    // Explicit play wins over paused state (needed for video export).
    if (play && !preview) {
      window.__AURA_LEGACY_PAUSED = false;
      previewMode = false;
      invokeAnimateBeat(normalized, "play");
    } else if (preview || window.__AURA_LEGACY_PAUSED) {
      previewMode = true;
      invokeAnimateBeat(normalized, "preview");
    } else {
      previewMode = false;
      invokeAnimateBeat(normalized, "play");
    }
    postProgress();
    return true;
  }

  function findButton(action) {
    const matchers = {
      prev: text => /上一|prev|‹|←/i.test(text),
      next: text => /下一|next|›|→/i.test(text),
      replay: text => /重播|replay|↻|restart/i.test(text),
      pause: text => /暂停|播放|pause|play|Ⅱ|▶/i.test(text),
    };
    return [...document.querySelectorAll("button")].find(button => {
      const text = [
        button.getAttribute("data-action"),
        button.getAttribute("aria-label"),
        button.textContent,
      ].filter(Boolean).join(" ");
      return text.includes(action) || matchers[action](text);
    }) || null;
  }

  function runAction(action, delta = 0) {
    if (action === "prev" || action === "next") {
      const state = activeIndex();
      if (enterBeat(state.index + delta, window.__AURA_LEGACY_PAUSED ? { preview: true } : { play: true })) return true;
    }
    if (action === "replay") {
      window.__AURA_LEGACY_PAUSED = false;
      previewMode = false;
      resumeGlobalTimeline();
      enterBeat(currentBeatIndex >= 0 ? currentBeatIndex : activeIndex().index, { play: true });
      return true;
    }
    const button = findButton(action);
    if (button) {
      button.click();
      setTimeout(postProgress, 0);
      return true;
    }
    postProgress();
    return false;
  }

  window.__AURA_LEGACY_PAUSE = () => {
    window.__AURA_LEGACY_PAUSED = true;
    if (currentBeatAnimation && typeof currentBeatAnimation.pause === "function") {
      try { currentBeatAnimation.pause(); } catch (e) {}
    }
    pauseGlobalTimeline();
    pauseCssAnimations();
  };

  window.__AURA_LEGACY_PLAY = () => {
    window.__AURA_LEGACY_PAUSED = false;
    resumeGlobalTimeline();
    playCssAnimations();
    if (previewMode) {
      previewMode = false;
      invokeAnimateBeat(currentBeatIndex >= 0 ? currentBeatIndex : 0, "play");
      return;
    }
    if (currentBeatAnimation && typeof currentBeatAnimation.play === "function") {
      try { currentBeatAnimation.play(); } catch (e) {}
      return;
    }
    requestAnimationFrame(replayAnimationsFallback);
  };

  function setPaused(nextPaused) {
    if (nextPaused) window.__AURA_LEGACY_PAUSE();
    else window.__AURA_LEGACY_PLAY();
    postProgress();
  }

  function initializeBridge() {
    try {
      freezeAllAnimations();
      enterBeat(0, { preview: true });
      window.__AURA_LEGACY_PAUSED = true;
      previewMode = true;
      if (currentBeatAnimation && typeof currentBeatAnimation.pause === "function") {
        try { currentBeatAnimation.pause(); } catch (e) {}
      }
      freezeAllAnimations();
      postProgress(READY);
    } catch (e) {
      parent.postMessage({
        type: READY,
        total: 0,
        index: 0,
        bridgeReady: false,
        gsapReady: gsapReady(),
        error: String((e && e.message) || e),
      }, "*");
    }
  }

  window.__AURA_BRIDGE = {
    enterBeat,
    play: () => window.__AURA_LEGACY_PLAY(),
    pause: () => window.__AURA_LEGACY_PAUSE(),
    replay: () => {
      window.__AURA_LEGACY_PAUSED = false;
      previewMode = false;
      resumeGlobalTimeline();
      enterBeat(currentBeatIndex >= 0 ? currentBeatIndex : activeIndex().index, { play: true });
    },
    freeze: freezeAllAnimations,
  };

  window.addEventListener("message", event => {
    if (event.source !== parent) return;
    const message = event.data;
    if (!isControlMessage(message)) return;
    if (message.action === "pause") setPaused(message.paused);
    else if (message.action === "play") setPaused(false);
    else if (message.action === "beat") {
      enterBeat(message.beatIndex, window.__AURA_LEGACY_PAUSED ? { preview: true } : { play: true });
    }
    else if (message.action === "seek") {
      const beatIndex = Number.isInteger(message.beatIndex) ? message.beatIndex : 0;
      if (window.__AURA_LEGACY_PAUSED) enterBeat(beatIndex, { preview: true });
      else enterBeat(beatIndex, { play: true });
      if (window.__AURA_LEGACY_PAUSED) freezeAllAnimations();
    }
    else if (message.action === "prev") runAction("prev", -1);
    else if (message.action === "next") runAction("next", 1);
    else if (message.action === "replay") runAction("replay");
    else if (message.action === "progress") postProgress();
  });

  try {
    const observer = new MutationObserver(() => postProgress());
    beats().forEach(beat => {
      observer.observe(beat, { attributes: true, attributeFilter: ["class"] });
    });
  } catch (e) {}

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeBridge, { once: true });
  } else {
    initializeBridge();
  }
  window.addEventListener("load", () => postProgress(READY));
})();
${closeScript}`
}

export function escapeJsonForHtml(value: string) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003C')
    .replace(/>/g, '\\u003E')
    .replace(/&/g, '\\u0026')
}

const NAKED_ANIMATION_JS = /(?:window\.animateBeat\d+\s*=|(?:const|let|var)\s+\w+\s*=\s*gsap\.timeline\s*\(|\.fromTo\s*\()/i

const ANIMATION_ERROR_HTML = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>html,body{height:100%;margin:0;background:#050505;color:#f5f5f7;font-family:system-ui,sans-serif}body{display:grid;place-items:center}.error{max-width:520px;padding:24px;text-align:center}.error p{color:#a1a1aa;line-height:1.6}</style></head><body><div class="error"><h2>动画内容解析失败</h2><p>生成的动画脚本结构不完整，请重新生成该动画。</p></div></body></html>'

const CSP_META = '<meta http-equiv="Content-Security-Policy" content="' +
  "default-src 'none'; " +
  "script-src 'unsafe-inline' https://cdnjs.cloudflare.com/ajax/libs/gsap/ https://cdn.jsdelivr.net/npm/gsap@ https://unpkg.com/gsap@; " +
  "style-src 'unsafe-inline' https://fonts.googleapis.com; " +
  "img-src data: https:; " +
  "font-src 'self' data: https://fonts.gstatic.com; " +
  "connect-src 'none'; " +
  "frame-src 'none'" +
  '">'

const CONTROL_HIDE_STYLE = '<style>.animation-control-bar,nav[aria-label="动画控制"]{display:none!important}</style>'

/** Scale fixed 1920×1080 #stage into the iframe viewport (jacky-motion host contract). */
const STAGE_FIT_STYLE = '<style id="aura-stage-fit-style">html,body{margin:0!important;width:100%!important;height:100%!important;overflow:hidden!important;background:#050505}body{display:block!important;place-items:unset!important;min-height:0!important}#stage{position:absolute!important;transform-origin:top left}</style>'

function buildStageFitScript() {
  const closeScript = '<' + '/script>'
  return `<script id="aura-stage-fit">
(() => {
  const STAGE_W = 1920;
  const STAGE_H = 1080;
  function fitStage() {
    const stage = document.getElementById("stage");
    if (!stage) return;
    const vw = window.innerWidth || document.documentElement.clientWidth || STAGE_W;
    const vh = window.innerHeight || document.documentElement.clientHeight || STAGE_H;
    const scale = Math.min(vw / STAGE_W, vh / STAGE_H);
    stage.style.width = STAGE_W + "px";
    stage.style.height = STAGE_H + "px";
    stage.style.transformOrigin = "top left";
    stage.style.transform = "scale(" + scale + ")";
    stage.style.left = Math.max(0, (vw - STAGE_W * scale) / 2) + "px";
    stage.style.top = Math.max(0, (vh - STAGE_H * scale) / 2) + "px";
    stage.style.position = "absolute";
  }
  function scheduleFit() {
    fitStage();
    requestAnimationFrame(fitStage);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleFit, { once: true });
  } else {
    scheduleFit();
  }
  window.addEventListener("resize", fitStage);
  window.addEventListener("load", fitStage);
})();
${closeScript}`
}

function injectHeadAssets(html: string, assets: string) {
  if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, match => match + assets)
  return assets + html
}

function repairAndValidate(raw: string) {
  const repaired = repairDanglingAnimationScript(String(raw))
  if (hasNakedAnimationScript(repaired)) return { html: ANIMATION_ERROR_HTML, valid: false }
  return { html: repaired, valid: true }
}

/** Repair the common LLM failure where the final </script> appears before the remaining animation JS. */
export function repairDanglingAnimationScript(raw: string) {
  const bodyClose = raw.search(/<\/body\s*>/i)
  if (bodyClose < 0) return raw
  const beforeBody = raw.slice(0, bodyClose)
  const scriptClose = beforeBody.toLowerCase().lastIndexOf('</script>')
  if (scriptClose < 0) return raw
  const tailStart = scriptClose + '</script>'.length
  const tail = beforeBody.slice(tailStart).trim()
  if (!tail || !NAKED_ANIMATION_JS.test(tail) || /<\/?[a-z][^>]*>/i.test(tail)) return raw
  return beforeBody.slice(0, scriptClose) + '\n' + tail + '\n</script>' + raw.slice(bodyClose)
}

export function hasNakedAnimationScript(raw: string) {
  const withoutScripts = raw.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, '')
  return NAKED_ANIMATION_JS.test(withoutScripts)
}

/** Single-iframe HTML for AnimationPlayer — bridge + stage fit injected, no autoplay wrapper. */
export function prepareAnimationHtmlForPlayer(raw: string) {
  if (!raw) return ''
  const { html } = repairAndValidate(raw)
  const legacyBridge = buildLegacyBridgeScript()
  const assets = CSP_META + STAGE_FIT_STYLE + legacyBridge + buildStageFitScript() + CONTROL_HIDE_STYLE
  return injectHeadAssets(html, assets)
}

export function playerHtmlScalesStageToViewport(source: string) {
  return source.includes('aura-stage-fit')
    && source.includes('function fitStage')
    && source.includes('STAGE_W = 1920')
    && source.includes('STAGE_H = 1080')
    && source.includes('transform = "scale(" + scale + ")"')
}

export function normalizeAnimationHtml(raw: string) {
  if (!raw) return ''
  const { html } = repairAndValidate(raw)
  const payload = escapeJsonForHtml(injectHeadAssets(html, CSP_META))
  const closeScript = '<' + '/script>'
  const legacyBridge = buildLegacyBridgeScript()
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; width: 100vw; height: 100vh; overflow: hidden; background: #050505; }
    .viewport { position: relative; width: 100vw; height: 100vh; display: grid; place-items: center; overflow: hidden; background: #050505; }
    .stage { position: relative; width: min(100vw, calc(100vh * 16 / 9)); height: min(100vh, calc(100vw * 9 / 16)); aspect-ratio: 16 / 9; overflow: hidden; background: #050505; }
    iframe { position: absolute; width: 1920px; height: 1080px; border: 0; transform-origin: top left; background: #050505; }
    .legacy-control-bar { position: absolute; left: 50%; bottom: 10px; z-index: 20; transform: translateX(-50%); display: flex; gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid rgba(255,255,255,.16); border-radius: 14px; background: rgba(0,0,0,.68); backdrop-filter: blur(16px); }
    .legacy-control-bar button { width: 38px; height: 34px; border: 1px solid rgba(255,255,255,.16); border-radius: 10px; background: rgba(255,255,255,.08); color: #f5f5f7; cursor: pointer; font-size: 16px; }
    .legacy-control-bar button:hover { background: rgba(255,255,255,.16); }
    .legacy-progress { min-width: 46px; text-align: center; color: rgba(245,245,247,.68); font: 12px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; font-variant-numeric: tabular-nums; }
  </style>
</head>
<body>
  <div class="viewport">
    <div class="stage">
      <iframe title="教学动画内容" allow="autoplay" sandbox="allow-scripts"></iframe>
      <nav class="legacy-control-bar" aria-label="动画控制">
        <button type="button" data-action="prev" aria-label="上一页">‹</button>
        <button type="button" data-action="pause" aria-label="暂停">Ⅱ</button>
        <button type="button" data-action="replay" aria-label="重播">↻</button>
        <button type="button" data-action="next" aria-label="下一页">›</button>
        <span class="legacy-progress" aria-live="polite"></span>
      </nav>
    </div>
  </div>
  <script type="application/json" id="animation-html">${payload}${closeScript}
  <script>
    (() => {
      const stage = document.querySelector('.stage');
      const frame = document.querySelector('iframe');
      const pauseButton = document.querySelector('[data-action="pause"]');
      const progress = document.querySelector('.legacy-progress');
      let paused = true;
      const raw = JSON.parse(document.getElementById('animation-html').textContent || '""');
      const legacyBridge = ${escapeJsonForHtml(legacyBridge)};
      const controlHideStyle = '${CONTROL_HIDE_STYLE}';
      const instrumented = /<head[^>]*>/i.test(raw)
        ? raw.replace(/<head[^>]*>/i, match => match + legacyBridge + controlHideStyle)
        : legacyBridge + controlHideStyle + raw;
      frame.srcdoc = instrumented;

      function fit() {
        const rect = stage.getBoundingClientRect();
        const scale = Math.min(rect.width / 1920, rect.height / 1080);
        frame.style.transform = 'scale(' + scale + ')';
        frame.style.left = Math.max(0, (rect.width - 1920 * scale) / 2) + 'px';
        frame.style.top = Math.max(0, (rect.height - 1080 * scale) / 2) + 'px';
      }

      function sendInnerAction(action, extra = {}) {
        frame.contentWindow?.postMessage({ type: '${LEGACY_CONTROL_TYPE}', action, ...extra }, '*');
      }

      function setPaused(nextPaused) {
        paused = nextPaused;
        pauseButton.textContent = paused ? '▶' : 'Ⅱ';
        pauseButton.setAttribute('aria-label', paused ? '播放' : '暂停');
        sendInnerAction('pause', { paused });
      }

      document.querySelector('.legacy-control-bar').addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        const action = button.getAttribute('data-action');
        if (action === 'pause') {
          setPaused(!paused);
          return;
        }
        if (action === 'prev' || action === 'next' || action === 'replay') {
          sendInnerAction(action);
        }
      });

      window.addEventListener('message', event => {
        if (event.source === window.parent) {
          const message = event.data;
          if (message && typeof message === 'object' && message.type === '${LEGACY_CONTROL_TYPE}') {
            sendInnerAction(message.action, message);
            if (message.action === 'play') {
              paused = false;
              pauseButton.textContent = 'Ⅱ';
              pauseButton.setAttribute('aria-label', '暂停');
            } else if (message.action === 'pause') {
              paused = !!message.paused;
              pauseButton.textContent = paused ? '▶' : 'Ⅱ';
              pauseButton.setAttribute('aria-label', paused ? '播放' : '暂停');
            }
            return;
          }
        }
        if (event.source !== frame.contentWindow) return;
        const message = event.data;
        const isProgressMessage = message
          && typeof message === 'object'
          && (message.type === '${LEGACY_PROGRESS_TYPE}' || message.type === '${LEGACY_READY_TYPE}')
          && Number.isFinite(message.index)
          && Number.isFinite(message.total)
          && message.index >= 0
          && message.total >= 0;
        if (!isProgressMessage) return;
        progress.textContent = message.total ? message.index + ' / ' + message.total : '';
      });
      window.addEventListener('resize', fit);
      frame.addEventListener('load', () => {
        fit();
        sendInnerAction('progress');
      });
      requestAnimationFrame(fit);
    })();
  ${closeScript}
</body>
</html>`
}

export function bridgeUsesAnimateBeatContract(source: string) {
  return source.includes('window.animateBeat') && source.includes('invokeAnimateBeat')
}

export function bridgeExposesAuraBridge(source: string) {
  return source.includes('window.__AURA_BRIDGE') && source.includes('enterBeat')
}

export function bridgeFreezesOnInit(source: string) {
  return source.includes('freezeAllAnimations') && source.includes('initializeBridge')
}

export function bridgeUsesPreviewMode(source: string) {
  return source.includes('previewMode') && source.includes('finishTimelinePreview')
}

export function bridgeRestartsFromPreviewOnPlay(source: string) {
  return source.includes('if (previewMode)') && source.includes('invokeAnimateBeat(currentBeatIndex >= 0 ? currentBeatIndex : 0, "play")')
}

export function bridgeResumesGlobalTimelineBeforeBeatPlay(source: string) {
  const playFn = source.indexOf('window.__AURA_LEGACY_PLAY = () => {')
  const resumeInPlay = source.indexOf('resumeGlobalTimeline();', playFn)
  const restartBeat = source.indexOf('invokeAnimateBeat(currentBeatIndex >= 0 ? currentBeatIndex : 0, "play")', playFn)
  return playFn >= 0 && resumeInPlay > playFn && restartBeat > resumeInPlay
}

export function bridgePausesBeatAndGlobalTimeline(source: string) {
  const pauseFn = source.indexOf('window.__AURA_LEGACY_PAUSE = () => {')
  const beatPause = source.indexOf('currentBeatAnimation.pause', pauseFn)
  const globalPause = source.indexOf('pauseGlobalTimeline();', pauseFn)
  return pauseFn >= 0 && beatPause > pauseFn && globalPause > beatPause
}

export function bridgeUsesWaapiCapabilityGuards(source: string) {
  return source.includes('getDocumentAnimations')
    && source.includes('typeof document.getAnimations !== "function"')
    && source.includes('bridgeReady')
    && source.includes('gsapReady')
}

export function getLegacyBridgeScriptSource() {
  return buildLegacyBridgeScript()
}
