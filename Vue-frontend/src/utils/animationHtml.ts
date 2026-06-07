const LEGACY_CONTROL_TYPE = '__AURA_LEGACY_CONTROL__'
const LEGACY_PROGRESS_TYPE = '__AURA_LEGACY_PROGRESS__'
const LEGACY_READY_TYPE = '__AURA_LEGACY_READY__'

function buildLegacyBridgeScript() {
  const closeScript = '<' + '/script>'
  return `<script>
(() => {
  const CONTROL = "${LEGACY_CONTROL_TYPE}";
  const PROGRESS = "${LEGACY_PROGRESS_TYPE}";
  const READY = "${LEGACY_READY_TYPE}";
  const ALLOWED_ACTIONS = new Set(["pause", "prev", "next", "replay", "progress"]);
  const nativeSetInterval = window.setInterval.bind(window);
  window.__AURA_LEGACY_PAUSED = false;
  window.setInterval = (fn, delay, ...args) => nativeSetInterval(() => {
    if (!window.__AURA_LEGACY_PAUSED) fn(...args);
  }, delay);

  function isControlMessage(message) {
    return !!message
      && typeof message === "object"
      && message.type === CONTROL
      && ALLOWED_ACTIONS.has(message.action)
      && (message.action !== "pause" || typeof message.paused === "boolean");
  }

  function beats() {
    return [...document.querySelectorAll(".beat")];
  }

  function activeIndex() {
    const items = beats();
    const index = items.findIndex(beat => beat.classList.contains("active"));
    return { beats: items, index: Math.max(0, index) };
  }

  function postProgress(type = PROGRESS) {
    const state = activeIndex();
    parent.postMessage({
      type,
      total: state.beats.length,
      index: state.beats.length ? state.index + 1 : 0,
    }, "*");
  }

  function replayAnimations() {
    const active = document.querySelector(".beat.active") || document.body;
    active?.getAnimations({ subtree: true }).forEach(animation => {
      animation.cancel();
      animation.play();
    });
  }

  function showBeat(nextIndex) {
    const state = activeIndex();
    if (!state.beats.length) return false;
    const normalized = ((nextIndex % state.beats.length) + state.beats.length) % state.beats.length;
    state.beats.forEach((beat, index) => beat.classList.toggle("active", index === normalized));
    postProgress();
    requestAnimationFrame(replayAnimations);
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
      if (showBeat(state.index + delta)) return true;
    }
    if (action === "replay") {
      replayAnimations();
      postProgress();
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
    document.getAnimations({ subtree: true }).forEach(animation => animation.pause());
  };

  window.__AURA_LEGACY_PLAY = () => {
    window.__AURA_LEGACY_PAUSED = false;
    document.getAnimations({ subtree: true }).forEach(animation => animation.play());
  };

  function setPaused(nextPaused) {
    const innerPause = findButton("pause");
    if (nextPaused) {
      if (innerPause && /暂停|pause|Ⅱ/i.test((innerPause.getAttribute("aria-label") || "") + innerPause.textContent)) {
        innerPause.click();
      }
      window.__AURA_LEGACY_PAUSE();
    } else {
      if (innerPause && /播放|play|▶/i.test((innerPause.getAttribute("aria-label") || "") + innerPause.textContent)) {
        innerPause.click();
      }
      window.__AURA_LEGACY_PLAY();
    }
    postProgress();
  }

  window.addEventListener("message", event => {
    if (event.source!==parent) return;
    const message = event.data;
    if (!isControlMessage(message)) return;
    if (message.action === "pause") setPaused(message.paused);
    else if (message.action === "prev") runAction("prev", -1);
    else if (message.action === "next") runAction("next", 1);
    else if (message.action === "replay") runAction("replay");
    else if (message.action === "progress") postProgress();
  });

  document.addEventListener("DOMContentLoaded", () => postProgress(READY));
  window.addEventListener("load", () => postProgress(READY));
  setTimeout(() => postProgress(READY), 0);
})();
${closeScript}`
}

export function escapeJsonForHtml(value: string) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003C')
    .replace(/>/g, '\\u003E')
    .replace(/&/g, '\\u0026')
}

export function normalizeAnimationHtml(raw: string) {
  if (!raw) return ''
  const html = String(raw)

  const payload = escapeJsonForHtml(html)
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
      let paused = false;
      let autoplayTimer = null;
      const raw = JSON.parse(document.getElementById('animation-html').textContent || '""');
      const legacyBridge = ${escapeJsonForHtml(legacyBridge)};
      const controlHideStyle = '<style>.animation-control-bar,nav[aria-label="动画控制"]{display:none!important}</style>';
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
        const allowedActions = new Set(['pause', 'prev', 'next', 'replay', 'progress']);
        if (!allowedActions.has(action)) return;
        frame.contentWindow?.postMessage({ type: '${LEGACY_CONTROL_TYPE}', action, ...extra }, '*');
      }

      function setPaused(nextPaused) {
        paused = nextPaused;
        pauseButton.textContent = paused ? '▶' : 'Ⅱ';
        pauseButton.setAttribute('aria-label', paused ? '播放' : '暂停');
        sendInnerAction('pause', { paused });
      }

      function startAutoplay() {
        if (autoplayTimer) clearInterval(autoplayTimer);
        autoplayTimer = setInterval(() => {
          if (paused) return;
          sendInnerAction('next');
        }, 4200);
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
        startAutoplay();
      });

      window.addEventListener('message', event => {
        if (event.source!==frame.contentWindow) return;
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
        startAutoplay();
      });
      requestAnimationFrame(fit);
    })();
  ${closeScript}
</body>
</html>`
}
