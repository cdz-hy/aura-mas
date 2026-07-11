import re
from pathlib import Path

# Keep in sync with Vue-frontend/src/utils/animationHtml.ts
# (buildLegacyBridgeScript + stage fit for prepareAnimationHtmlForPlayer)

CSP_META = (
    '<meta http-equiv="Content-Security-Policy" content="'
    "default-src 'none'; "
    "script-src 'unsafe-inline' https://cdnjs.cloudflare.com/ajax/libs/gsap/ https://cdn.jsdelivr.net/npm/gsap@ https://unpkg.com/gsap@; "
    "style-src 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src data: https:; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'none'; "
    "frame-src 'none'"
    '">'
)

CONTROL_HIDE_STYLE = '<style>.animation-control-bar,nav[aria-label="动画控制"]{display:none!important}</style>'

STAGE_FIT_STYLE = (
    '<style id="aura-stage-fit-style">'
    "html,body{margin:0!important;width:100%!important;height:100%!important;overflow:hidden!important;background:#050505}"
    "body{display:block!important;place-items:unset!important;min-height:0!important}"
    "#stage{position:absolute!important;transform-origin:top left}"
    "</style>"
)

STAGE_FIT_SCRIPT = """<script id="aura-stage-fit">
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
</script>"""

_BRIDGE_PATH = Path(__file__).with_name("legacy_bridge.js")


def _build_legacy_bridge_script() -> str:
    return f"<script>{_BRIDGE_PATH.read_text(encoding='utf-8')}</script>"


def inject_head_assets(html: str, assets: str) -> str:
    if re.search(r"<head[^>]*>", html, re.I):
        return re.sub(r"(<head[^>]*>)", r"\1" + assets, html, count=1, flags=re.I)
    return assets + html


def prepare_animation_html(raw: str) -> str:
    """Inject playback bridge + stage fit for export/player — mirrors prepareAnimationHtmlForPlayer."""
    if not raw:
        return ""
    assets = CSP_META + STAGE_FIT_STYLE + _build_legacy_bridge_script() + STAGE_FIT_SCRIPT + CONTROL_HIDE_STYLE
    return inject_head_assets(raw, assets)
