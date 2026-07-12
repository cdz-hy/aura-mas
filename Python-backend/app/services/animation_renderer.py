"""
动画视频渲染器：Playwright 录屏 + FFmpeg 合成。

系统依赖（不在 requirements.txt 中，需手动安装）：
  - ffmpeg / ffprobe：winget install FFmpeg | choco install ffmpeg | scoop install ffmpeg
  - Chromium：python -m playwright install chromium
"""
import logging
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from app.services.animation_export import QUALITIES
from app.services.animation_html import prepare_animation_html

logger = logging.getLogger("services.animation_renderer")

SYSTEM_BROWSERS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)


def _ass_time(milliseconds: int) -> str:
    centiseconds = max(0, milliseconds) // 10
    seconds, cs = divmod(centiseconds, 100)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours}:{minute:02d}:{sec:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return str(text).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def build_ass(cues: list[dict], width: int, height: int) -> str:
    font_size = 54 if height >= 1080 else 36
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,56,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [
        f"Dialogue: 0,{_ass_time(c['startMs'])},{_ass_time(c['endMs'])},Default,,0,0,0,,{_ass_escape(c['text'])}"
        for c in cues
    ]
    return header + "\n".join(events) + "\n"


def dependency_status() -> dict[str, bool]:
    """Check runtime dependencies. Install missing ones before using video export:
    ffmpeg/ffprobe: winget install FFmpeg
    Chromium:       python -m playwright install chromium
    """
    browser_root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path.home() / "AppData/Local/ms-playwright"))
    chromium = any(browser_root.glob("chromium-*/chrome-win*/chrome.exe")) or any(
        browser_root.glob("chromium_headless_shell-*/chrome-headless-shell-win*/chrome-headless-shell.exe")
    ) or any(path.exists() for path in SYSTEM_BROWSERS)
    return {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")), "chromium": chromium}


def _candidate_audio_urls(audio_url: str) -> list[str]:
    """Prefer rewritten public Qiniu domain, then the original URL."""
    candidates: list[str] = []
    try:
        from app.services.qiniu_client import qiniu_client

        rewritten = qiniu_client.rewrite_to_public_url(audio_url)
        if rewritten:
            candidates.append(rewritten)
    except Exception as exc:
        logger.warning("audio URL rewrite skipped: %s", exc)
    if audio_url and audio_url not in candidates:
        candidates.append(audio_url)
    return candidates


def download_narration_audio(audio_url: str, dest: Path) -> bool:
    """Download narration audio for muxing. Returns False on failure (export continues silent)."""
    last_error: Exception | None = None
    for url in _candidate_audio_urls(audio_url):
        try:
            urllib.request.urlretrieve(url, dest)
            if dest.exists() and dest.stat().st_size > 0:
                return True
            dest.unlink(missing_ok=True)
            last_error = RuntimeError(f"empty audio download from {url}")
        except Exception as exc:
            last_error = exc
            dest.unlink(missing_ok=True)
            logger.warning("narration audio download failed via %s: %s", url, exc)
    if last_error:
        logger.warning("export will continue without audio: %s", last_error)
    return False


def render_animation(module_data: dict, quality: str, output_path: str) -> None:
    """Synchronous entry point. Works in standalone scripts and worker processes."""
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_render_animation_async(module_data, quality, output_path))
        return
    # Called from within an event loop (e.g. via asyncio.to_thread) — run in a fresh loop
    import threading
    result = [None]
    def _run():
        try:
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            asyncio.run(_render_animation_async(module_data, quality, output_path))
        except Exception as e:
            result[0] = e
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join()
    if result[0]:
        raise result[0]


async def _render_animation_async(module_data: dict, quality: str, output_path: str) -> None:
    """Core render logic using async Playwright (works inside asyncio contexts)."""
    from playwright.async_api import async_playwright

    width, height = QUALITIES[quality]
    narration = module_data["narration"]
    duration_ms = max(1, round(float(narration["duration"]) * 1000))
    missing = [name for name, ready in dependency_status().items() if not ready and name != "ffprobe"]
    if missing:
        raise RuntimeError("Missing animation export dependencies: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="aura-animation-") as temp_dir:
        temp = Path(temp_dir)
        html_file = temp / "animation.html"
        video_file = temp / "capture.webm"
        audio_file = temp / "narration.wav"
        subtitle_file = temp / "subtitles.ass"
        html_file.write_text(prepare_animation_html(module_data["html"]), encoding="utf-8")
        subtitle_file.write_text(build_ass(narration["cues"], width, height), encoding="utf-8-sig")
        if narration.get("audioUrl") and narration.get("audioStatus", "ready") == "ready":
            download_narration_audio(str(narration["audioUrl"]), audio_file)

        async with async_playwright() as playwright:
            bundled = Path(playwright.chromium.executable_path)
            executable = bundled if bundled.exists() else next((path for path in SYSTEM_BROWSERS if path.exists()), None)
            browser = await playwright.chromium.launch(headless=True, executable_path=str(executable) if executable else None)
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=str(temp), record_video_size={"width": width, "height": height},
            )
            page = await context.new_page()
            await page.goto(html_file.as_uri(), wait_until="networkidle")
            await page.evaluate("""() => {
              document.querySelectorAll('.animation-control-bar, nav[aria-label="动画控制"]').forEach(el => el.remove());
            }""")
            await page.wait_for_function("() => window.__AURA_BRIDGE", timeout=15000)
            current_beat = None
            for cue in narration["cues"]:
                beat_index = int(cue["beatIndex"])
                duration = max(1, int(cue["endMs"]) - int(cue["startMs"]))
                if beat_index != current_beat:
                    await page.evaluate("() => window.__AURA_BRIDGE.pause()")
                    await page.evaluate("(idx) => window.__AURA_BRIDGE.enterBeat(idx, { play: true })", beat_index)
                    current_beat = beat_index
                else:
                    await page.evaluate("() => window.__AURA_BRIDGE.play()")
                await page.wait_for_timeout(duration)
            await page.evaluate("() => window.__AURA_BRIDGE.freeze()")
            recorded = page.video
            await page.close()
            await context.close()
            await browser.close()
            Path(await recorded.path()).replace(video_file)

        # Windows: absolute ASS paths break libass (drive colon escaping). Use cwd-relative names.
        output_abs = str(Path(output_path).resolve())
        command = ["ffmpeg", "-y", "-i", video_file.name]
        if audio_file.exists():
            command += ["-i", audio_file.name]
        command += [
            "-vf", f"ass={subtitle_file.name}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        ]
        if audio_file.exists():
            command += ["-c:a", "aac", "-b:a", "192k"]
        command += ["-t", f"{duration_ms / 1000:.3f}", "-movflags", "+faststart", output_abs]
        result = subprocess.run(
            command,
            cwd=str(temp),
            capture_output=True,
            text=True,
            timeout=max(120, duration_ms // 1000 * 4),
        )
        if result.returncode:
            raise RuntimeError("FFmpeg export failed: " + result.stderr[-1200:])
