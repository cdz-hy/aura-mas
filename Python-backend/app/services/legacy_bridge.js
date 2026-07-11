(() => {
  const CONTROL = "__AURA_LEGACY_CONTROL__";
  const PROGRESS = "__AURA_LEGACY_PROGRESS__";
  const READY = "__AURA_LEGACY_READY__";
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
          // Global timeline must be running before the beat timeline is created/restarted.
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
    // Otherwise paused/preview shows the completed beat; playing restarts from 0%.
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
    // Resume global timeline before recreating/restarting the beat timeline.
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
