# aura-mas

## Animation narration and video export

New animation resources include synchronized MiMo TTS narration and subtitle cues. Start the dedicated export worker separately from the FastAPI process:

```powershell
cd Python-backend
python -m app.workers.animation_export_worker
```

The worker consumes the durable RabbitMQ queue `ai.animation.export`. Its runtime requires `ffmpeg`, `ffprobe`, Playwright Chromium (`playwright install chromium`), and a Chinese font such as Microsoft YaHei or Noto Sans CJK. Exported H.264/AAC MP4 files are uploaded to the configured Qiniu bucket under `animation-video/`. Missing Chromium or FFmpeg produces a diagnostic export failure; animation playback and subtitle-only narration remain available.
