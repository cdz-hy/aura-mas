import io
import logging
import re
import wave
from html.parser import HTMLParser
from typing import Callable

from app.services.qiniu_client import qiniu_client

logger = logging.getLogger("services.animation_narration")
MAX_CUE_DURATION_MS = 120_000


class _BeatTextParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    IGNORED_TAGS = {"script", "style", "nav", "button"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.ignored_depth = 0
        self.parts: list[list[str]] = []
        self.narrations: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.depth and tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            if tag not in self.VOID_TAGS:
                self.ignored_depth += 1
            return
        classes = dict(attrs).get("class", "").split()
        if self.depth and tag not in self.VOID_TAGS:
            self.depth += 1
        elif "beat" in classes:
            self.depth = 1
            self.parts.append([])
            self.narrations.append(re.sub(r"\s+", " ", dict(attrs).get("data-narration", "")).strip())

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.ignored_depth:
            self.ignored_depth -= 1
            return
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.ignored_depth and self.parts:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts[-1].append(text)


def extract_beat_texts(html: str) -> list[str]:
    parser = _BeatTextParser()
    parser.feed(html or "")
    if parser.narrations and len(parser.narrations) == len(parser.parts) and all(parser.narrations):
        return parser.narrations
    return ["。".join(parts)[:600] for parts in parser.parts if parts]


def narration_is_healthy(narration: dict) -> bool:
    cues = narration.get("cues") if isinstance(narration, dict) else None
    if narration.get("version") != 1 or not isinstance(cues, list) or not cues:
        return False
    if len(cues) > 30:
        return False
    code_pattern = re.compile(r"(?:gsap\.timeline|\.from(?:To)?\s*\(|window\.animateBeat|\b(?:const|let|var)\s+\w+\s*=)", re.I)
    for cue in cues:
        text = cue.get("text", "") if isinstance(cue, dict) else ""
        if not isinstance(text, str) or not text.strip() or len(text) > 800 or code_pattern.search(text):
            return False
        if not isinstance(cue.get("startMs"), (int, float)) or not isinstance(cue.get("endMs"), (int, float)):
            return False
        if cue["endMs"] <= cue["startMs"] or cue["endMs"] - cue["startMs"] > MAX_CUE_DURATION_MS:
            return False
    return True


def _wav_info(data: bytes) -> tuple[wave._wave_params, bytes, int]:
    with wave.open(io.BytesIO(data), "rb") as source:
        params = source.getparams()
        frames = source.readframes(source.getnframes())
        duration_ms = round(source.getnframes() * 1000 / source.getframerate())
    return params, frames, duration_ms


def build_pending_narration(html: str, voice: str = "冰糖") -> dict:
    """Build a pending narration structure with estimated durations based on text length.
    This allows the frontend to render the animation immediately without waiting for TTS.
    """
    texts = extract_beat_texts(html)
    if not texts:
        return {
            "version": 1,
            "voice": voice,
            "audioUrl": "",
            "audioStatus": "unavailable",
            "duration": 0,
            "cues": [],
        }
    
    # Estimate durations: 180ms per character, min 1800ms, max 10000ms
    durations = [max(1800, min(10000, len(text) * 180)) for text in texts]
    
    cues = []
    cursor = 0
    for index, (text, duration) in enumerate(zip(texts, durations)):
        cues.append({
            "beatIndex": index,
            "startMs": cursor,
            "endMs": cursor + duration,
            "text": text,
        })
        cursor += duration
        
    return {
        "version": 1,
        "voice": voice,
        "audioUrl": "",
        "audioStatus": "pending",
        "duration": cursor / 1000,
        "cues": cues,
    }


def build_narration(
    html: str,
    synthesize: Callable[[str, str], bytes],
    upload: Callable[[bytes, str, str], str] | None = None,
    voice: str = "冰糖",
) -> dict:
    """Build narration cues + audio URL.

    Matches podcast behavior: upload success → audioStatus=ready with the returned
    URL (HTTP or HTTPS). No post-upload HTTPS reachability gate.
    """
    texts = extract_beat_texts(html)
    if not texts:
        return {
            "version": 1,
            "voice": voice,
            "audioUrl": "",
            "audioStatus": "unavailable",
            "duration": 0,
            "cues": [],
        }

    audio_url = ""
    audio_status = "failed"
    audio_error: str | None = None
    durations: list[int] = []

    try:
        segments = [_wav_info(synthesize(text, voice)) for text in texts]
        params = segments[0][0]
        audio_format = (params.nchannels, params.sampwidth, params.framerate, params.comptype)
        if any(
            (segment[0].nchannels, segment[0].sampwidth, segment[0].framerate, segment[0].comptype) != audio_format
            for segment in segments
        ):
            raise ValueError("TTS WAV segments use incompatible audio formats")
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setparams(params)
            for _, frames, _ in segments:
                target.writeframes(frames)
        try:
            audio_url = (upload or qiniu_client.upload_bytes)(
                output.getvalue(), "animation_narration.wav", "animation-audio"
            )
            audio_status = "ready"
            durations = [segment[2] for segment in segments]
        except Exception as upload_exc:
            logger.warning("Animation narration upload failed; using subtitle fallback: %s", upload_exc)
            audio_status = "failed"
            audio_error = str(upload_exc)[:200]
            audio_url = ""
            durations = [max(1800, min(8000, len(text) * 180)) for text in texts]
    except Exception as exc:
        logger.warning("Animation narration TTS failed; using subtitle fallback: %s", exc)
        audio_status = "failed"
        audio_error = str(exc)[:200]
        durations = [max(1800, min(8000, len(text) * 180)) for text in texts]

    cues = []
    cursor = 0
    for index, (text, duration) in enumerate(zip(texts, durations)):
        cues.append({
            "beatIndex": index,
            "startMs": cursor,
            "endMs": cursor + duration,
            "text": text,
        })
        cursor += duration
    result = {
        "version": 1,
        "voice": voice,
        "audioUrl": audio_url,
        "audioStatus": audio_status,
        "duration": cursor / 1000,
        "cues": cues,
    }
    if audio_error:
        result["audioError"] = audio_error
    return result
