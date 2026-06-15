"""
多模态类型资源生成智能体 - 为指定类型（思维导图/总结/代码等）生成对应格式的学习资源
类似 quiz_generator 的直接生成流程，跳过 RAG 检索和内容编排
"""
import logging
import requests
import base64
from typing import Dict, Any, List
from app.core.config import settings
from app.services.qiniu_client import qiniu_client
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_resource_type_generator_llm
from app.prompts import RESOURCE_TYPE_GENERATOR_PROMPTS, RESOURCE_TYPE_GENERATOR_DEFAULT_PROMPT
from app.utils.token_recorder import record_from_mimo

logger = logging.getLogger("agents.resource_type_generator")


def synthesize_speech(text: str, voice: str = "冰糖") -> bytes:
    """调用 MiMo-V2.5-TTS API 进行语音合成，返回音频字节码"""
    url = f"{settings.MIMO_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MIMO_API_KEY}"
    }
    payload = {
        "model": "mimo-v2.5-tts",
        "messages": [
            {
                "role": "user",
                "content": "用温馨、自然、清晰的中文播报音色"
            },
            {
                "role": "assistant",
                "content": text
            }
        ],
        "audio": {
            "format": "wav",
            "voice": voice
        }
    }
    logger.info(f"  [TTS] 正在调用 MiMo-TTS 进行语音合成 (字数: {len(text)}, 音色: {voice})...")
    resp = requests.post(url, headers=headers, json=payload, timeout=300)
    if resp.status_code != 200:
        raise Exception(f"MIMO TTS API 调用失败 ({resp.status_code}): {resp.text}")
    
    result = resp.json()
    choices = result.get("choices", [])
    if not choices:
        raise Exception(f"MIMO TTS API 返回空 choices: {result}")
        
    audio_data = choices[0].get("message", {}).get("audio", {}).get("data")
    if not audio_data:
        raise Exception(f"MIMO TTS API 未返回音频数据: {result}")
        
    return base64.b64decode(audio_data)

def synthesize_long_speech(text: str, voice: str = "冰糖", chunk_size: int = 1000) -> bytes:
    """对长文本进行分段合成并合并为单个 WAV 字节码"""
    import io
    import wave
    import re
    
    sentences = re.split(r'([。！？.!?\n])', text)
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i] + sentences[i+1]
        if len(current_chunk) + len(sentence) > chunk_size:
            if current_chunk.strip():
                chunks.append(current_chunk)
            current_chunk = sentence
        else:
            current_chunk += sentence
            
    if sentences[-1]:
        current_chunk += sentences[-1]
    if current_chunk.strip():
        chunks.append(current_chunk)
        
    if not chunks:
        return b""
        
    if len(chunks) == 1:
        return synthesize_speech(chunks[0], voice)
        
    logger.info(f"  [TTS] 文本长度 {len(text)}，超过单次限制，分为 {len(chunks)} 段合成...")
    
    import concurrent.futures
    
    valid_chunks = [(idx, chunk) for idx, chunk in enumerate(chunks) if chunk.strip()]
    if not valid_chunks:
        raise Exception("所有的分段均为空")
        
    audio_segments = [None] * len(chunks)
    
    def _synthesize_task(task_idx, task_chunk):
        logger.info(f"  [TTS] 正在并发合成第 {task_idx+1}/{len(chunks)} 段 (字数: {len(task_chunk)})...")
        try:
            return task_idx, synthesize_speech(task_chunk, voice)
        except Exception as e:
            logger.error(f"  [TTS] 第 {task_idx+1} 段并发合成失败: {e}")
            raise e

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_synthesize_task, idx, chunk) for idx, chunk in valid_chunks]
        for future in concurrent.futures.as_completed(futures):
            task_idx, chunk_bytes = future.result()
            audio_segments[task_idx] = chunk_bytes
            
    # 去除空段对应的 None
    audio_segments = [seg for seg in audio_segments if seg is not None]
    
    if not audio_segments:
        raise Exception("所有的分段均合成失败")
        
    out_io = io.BytesIO()
    with wave.open(out_io, 'wb') as wav_out:
        for idx, segment in enumerate(audio_segments):
            seg_io = io.BytesIO(segment)
            try:
                with wave.open(seg_io, 'rb') as wav_in:
                    if idx == 0:
                        wav_out.setparams(wav_in.getparams())
                    wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
            except Exception as e:
                logger.error(f"  [TTS] 合并第 {idx+1} 段音频时失败: {e}")
                
    return out_io.getvalue()

# ==================== 各类型的系统提示 ====================


# 通用的默认提示


def resource_type_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    多模态类型资源生成智能体节点

    根据 state 中的资源类型，调用 LLM 生成对应格式的内容。
    类似 quiz_generator 的直接生成模式，不经过 RAG 和编排。
    """
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    task_breakdown = state.get("task_breakdown") or {}
    user_profile = state.get("user_profile", {})
    rag_chunks = state.get("rag_context_chunks", [])
    chat_history = state.get("chat_history", [])
    source_resource_content = state.get("source_resource_content", "")

    # 从 task_breakdown 中提取目标资源类型
    modules = task_breakdown.get("modules", [])
    resource_type = "text"
    module_title = ""
    module_desc = ""
    if modules:
        module = modules[0]
        module_title = module.get("title", "")
        module_desc = module.get("description", "")
        resources = module.get("resources", [])
        if resources:
            resource_type = resources[0].get("resource_type", "text")

    logger.info(f"{'='*60}")
    logger.info(f"  [类型资源生成] 开始处理")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    logger.info(f"  目标类型: {resource_type}")
    logger.info(f"  模块标题: {module_title}")

    llm = get_resource_type_generator_llm()

    # 选择对应的系统提示
    system_prompt = RESOURCE_TYPE_GENERATOR_PROMPTS.get(resource_type, RESOURCE_TYPE_GENERATOR_DEFAULT_PROMPT)

    # 构造学习内容摘要（优先用源资源全文，否则用 RAG）
    content_summary = ""
    if source_resource_content:
        content_summary = source_resource_content
        logger.info(f"  [类型资源生成] 使用源资源全文作为上下文 ({len(source_resource_content)} 字符)")
    elif rag_chunks:
        parts = []
        for i, chunk in enumerate(rag_chunks[:10]):
            heading = " > ".join(chunk.get("heading", []))
            doc_title = chunk.get("doc_title", "")
            content = chunk.get("content", "")[:300]
            parts.append(f"[资料{i+1}] 来源: {doc_title}\n章节: {heading}\n内容: {content}")
        content_summary = "\n\n---\n\n".join(parts)
        logger.info(f"  [类型资源生成] 使用 RAG 检索结果作为上下文 ({len(rag_chunks)} 块)")

    # 用户偏好
    behavior = user_profile.get("learning_behavior", {})
    vv = behavior.get("visual_vs_verbal", 0)
    pref_text = "视觉型" if vv < -0.3 else ("言语型" if vv > 0.3 else "均衡型")

    # 对话历史
    history_text = ""
    if chat_history:
        recent = chat_history[-4:]
        lines = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content'][:150]}")
        history_text = "\n".join(lines)

    # 构造用户消息
    user_content = f"""学习目标: {learning_goal}

对话历史:
{history_text if history_text else "无历史记录"}

当前模块信息:
- 标题: {module_title}
- 描述: {module_desc}
- 资源类型: {resource_type}

用户内容偏好: {pref_text}
"""

    if source_resource_content:
        user_content += f"\n## 源资源全文（请基于此内容生成）:\n{content_summary}\n"
    elif content_summary:
        user_content += f"\n## 检索到的相关知识资料:\n{content_summary}\n"
    else:
        user_content += "\n暂无检索到的知识资料，请基于学习目标自主生成。\n"

    user_content += f"\n请为该模块生成 {resource_type} 类型的学习资源，输出 JSON:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        logger.info(f"  [类型资源生成] 正在调用 LLM 生成 {resource_type}...")
        result = llm.chat_json(messages, max_tokens=8192)
        record_from_mimo(llm, state.get("user_id", 0), "resource_type_generation", state.get("task_id"))

        # 标准化输出
        generated = {
            "module_type": resource_type,
            "title": result.get("title", module_title),
            "description": result.get("description", module_desc),
            "content": "",
        }

        # mindmap 类型：content 字段是 nodeData 的 JSON 字符串
        if resource_type == "mindmap":
            node_data = result.get("nodeData")
            if node_data:
                import json
                generated["content"] = json.dumps(node_data, ensure_ascii=False)
            else:
                # 兼容 content 直接是 nodeData 的情况
                generated["content"] = result.get("content", "")
        elif resource_type == "podcast":
            title = result.get("title", module_title) or "未命名播客"
            description = result.get("description", module_desc) or ""
            paragraphs = result.get("paragraphs", [])

            # 如果没有 paragraphs，尝试从 content 解析或转换
            if not paragraphs and result.get("content"):
                paragraphs = [{"title": "正文", "text": result.get("content", "")}]

            audio_script = " ".join([p.get("text", "") for p in paragraphs])

            audio_url = ""
            warning_html = ""
            player_style = ""
            if audio_script:
                try:
                    audio_bytes = synthesize_long_speech(audio_script, voice="冰糖")
                    audio_url = qiniu_client.upload_bytes(audio_bytes, "podcast_audio.wav", "podcast-audio")
                    logger.info(f"  [TTS] 语音合成并上传成功: {audio_url}")
                except Exception as tts_err:
                    logger.error(f"  [TTS] 语音合成失败: {tts_err}")
                    warning_html = '<div class="warning-banner"> 语音合成服务暂时不可用，已为您降级为纯文本播客模式。</div>'
                    player_style = "display: none;"
            else:
                logger.warning("  [类型资源生成] 未生成 audio_script，隐藏播放器")
                player_style = "display: none;"

            # 构建卡片 HTML
            cards_html = ""
            for i, p in enumerate(paragraphs):
                p_title = p.get("title", "")
                p_text = p.get("text", "")
                card_title_html = f"<h2>{p_title}</h2>" if p_title else ""
                cards_html += f"""
            <div class="podcast-card" id="card-{i}" data-text="{p_text}" onclick="playCard({i})">
                <div class="card-header">
                    {card_title_html}
                    <div class="card-play-indicator">
                        <svg viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </div>
                </div>
                <p class="card-text">{p_text}</p>
            </div>"""

            # 组装完整的 HTML 页面
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0b12;
            --card-bg: rgba(255, 255, 255, 0.03);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --accent-color: #e85d36;
            --accent-glow: rgba(232, 93, 54, 0.15);
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-x: hidden;
            padding: 40px 20px;
        }}
        
        .glow-bg {{
            position: fixed;
            top: -10%;
            left: 50%;
            transform: translateX(-50%);
            width: 80vw;
            height: 50vh;
            background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
            z-index: -1;
            pointer-events: none;
        }}
        
        .container {{
            width: 100%;
            max-width: 800px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            line-height: 1.2;
            background: linear-gradient(135deg, #ffffff 0%, #a0aec0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }}
        
        .desc {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            line-height: 1.5;
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .player-panel {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(24px);
            border-radius: 20px;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 8px 32px rgba(0,0,0,.25);
            position: sticky;
            top: 20px;
            z-index: 100;
        }}
        
        .player-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }}
        
        .player-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .play-btn {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--accent-color);
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, background 0.2s;
            box-shadow: 0 4px 12px rgba(232, 93, 54, 0.3);
        }}
        
        .play-btn:hover {{
            transform: scale(1.05);
            background: #f06a45;
        }}
        
        .play-btn svg {{
            width: 20px;
            height: 20px;
            fill: currentColor;
        }}
        
        .track-info {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        .track-title {{
            font-weight: 600;
            font-size: 1rem;
        }}
        
        .track-speaker {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .player-right {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .toggle-container {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            color: var(--text-secondary);
            cursor: pointer;
            user-select: none;
        }}
        
        .switch {{
            position: relative;
            display: inline-block;
            width: 36px;
            height: 20px;
        }}
        
        .switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        
        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255,255,255,0.1);
            transition: .3s;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .slider:before {{
            position: absolute;
            content: "";
            height: 12px;
            width: 12px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }}
        
        input:checked + .slider {{
            background-color: var(--accent-color);
            border-color: var(--accent-color);
        }}
        
        input:checked + .slider:before {{
            transform: translateX(16px);
        }}
        
        .progress-container {{
            display: flex;
            align-items: center;
            gap: 12px;
            width: 100%;
        }}
        
        .time-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            min-width: 36px;
        }}
        
        .progress-bar-wrap {{
            flex: 1;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            position: relative;
            cursor: pointer;
        }}
        
        .progress-bar-fill {{
            height: 100%;
            background: var(--accent-color);
            border-radius: 3px;
            width: 0%;
            transition: width 0.1s linear;
        }}

        .download-btn {{
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-primary);
            text-decoration: none;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
            outline: none;
        }}
        
        .download-btn:hover {{
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }}
        
        @media (max-width: 600px) {{
            .player-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .player-right {{
                width: 100%;
                justify-content: space-between;
            }}
            h1 {{
                font-size: 2rem;
            }}
        }}
        
        .warning-banner {{
            background: rgba(232, 93, 54, 0.15);
            border: 1px solid rgba(232, 93, 54, 0.3);
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 0.9rem;
            color: #ffaa90;
            text-align: center;
        }}
        
        .podcast-content {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .podcast-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 28px;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(20px);
            opacity: 0.45;
            cursor: pointer;
            position: relative;
        }}
        
        .podcast-card:hover {{
            opacity: 0.8;
            transform: translateY(-2px);
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .podcast-card.active {{
            opacity: 1;
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(232, 93, 54, 0.5);
            box-shadow: 0 8px 32px rgba(232, 93, 54, 0.1), inset 0 1px 0 rgba(255,255,255,.05);
            transform: translateY(-4px);
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }}
        
        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.35rem;
            font-weight: 600;
        }}
        
        .card-play-indicator {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            transition: all 0.2s;
        }}
        
        .podcast-card:hover .card-play-indicator,
        .podcast-card.active .card-play-indicator {{
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }}
        
        .card-play-indicator svg {{
            width: 12px;
            height: 12px;
            fill: currentColor;
        }}
        
        p.card-text {{
            color: rgba(255, 255, 255, 0.85);
            font-size: 1.05rem;
            line-height: 1.7;
            text-align: justify;
        }}
    </style>
</head>
<body>
    <div class="glow-bg"></div>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p class="desc">{description}</p>
        </header>
        
        {warning_html}
        
        <div class="player-panel" style="{player_style}">
            <div class="player-row">
                <div class="player-left">
                    <button class="play-btn" id="playBtn" onclick="togglePlay()">
                        <svg viewBox="0 0 24 24" id="playIcon">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                        <svg viewBox="0 0 24 24" id="pauseIcon" style="display:none;">
                            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                        </svg>
                    </button>
                    <div class="track-info">
                        <span class="track-title">音频朗读</span>
                        <span class="track-speaker">配音音色：冰糖 (默认)</span>
                    </div>
                </div>
                <div class="player-right">
                    <button class="download-btn" onclick="downloadAudio()" title="下载音频">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                        </svg>
                        <span>下载音频</span>
                    </button>
                    <label class="toggle-container">
                        <span>文案自动跟随</span>
                        <div class="switch">
                            <input type="checkbox" id="followSwitch" checked onchange="toggleFollow()">
                            <span class="slider"></span>
                        </div>
                    </label>
                </div>
            </div>
            
            <div class="progress-container">
                <span class="time-label" id="currentTime">00:00</span>
                <div class="progress-bar-wrap" id="progressBar" onclick="seekAudio(event)">
                    <div class="progress-bar-fill" id="progressFill"></div>
                </div>
                <span class="time-label" id="duration">00:00</span>
            </div>
        </div>
        
        <div class="podcast-content" id="podcastContent">
            {cards_html}
        </div>
    </div>
    
    <script>
        const audioUrl = "{audio_url}";
        let audio = null;
        let isPlaying = false;
        let autoFollow = true;
        
        const cards = Array.from(document.querySelectorAll('.podcast-card'));
        const cardLengths = cards.map(card => card.dataset.text.length);
        const totalLength = cardLengths.reduce((a, b) => a + b, 0);
        
        const cumulativeLengths = [];
        let acc = 0;
        for (let len of cardLengths) {{
            acc += len;
            cumulativeLengths.push(acc);
        }}
        
        if (audioUrl) {{
            audio = new Audio(audioUrl);
            
            audio.addEventListener('timeupdate', () => {{
                updateProgress();
                if (autoFollow) {{
                    syncTextHighlight();
                }}
            }});
            
            audio.addEventListener('loadedmetadata', () => {{
                document.getElementById('duration').innerText = formatTime(audio.duration);
            }});
            
            audio.addEventListener('ended', () => {{
                isPlaying = false;
                updatePlayerState();
            }});
        }}
        
        function formatTime(secs) {{
            if (isNaN(secs)) return "00:00";
            const m = Math.floor(secs / 60).toString().padStart(2, '0');
            const s = Math.floor(secs % 60).toString().padStart(2, '0');
            return `${{m}}:${{s}}`;
        }}
        
        function togglePlay() {{
            if (!audio) return;
            if (isPlaying) {{
                audio.pause();
                isPlaying = false;
            }} else {{
                audio.play().catch(err => console.log("播放失败: ", err));
                isPlaying = true;
            }}
            updatePlayerState();
        }}
        
        function updatePlayerState() {{
            const playIcon = document.getElementById('playIcon');
            const pauseIcon = document.getElementById('pauseIcon');
            if (isPlaying) {{
                playIcon.style.display = 'none';
                pauseIcon.style.display = 'block';
            }} else {{
                playIcon.style.display = 'block';
                pauseIcon.style.display = 'none';
            }}
        }}
        
        function updateProgress() {{
            if (!audio) return;
            const cur = audio.currentTime;
            const dur = audio.duration || 1;
            const pct = (cur / dur) * 100;
            document.getElementById('progressFill').style.width = `${{pct}}%`;
            document.getElementById('currentTime').innerText = formatTime(cur);
        }}
        
        function seekAudio(e) {{
            if (!audio) return;
            const bar = document.getElementById('progressBar');
            const rect = bar.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const width = rect.width;
            const pct = clickX / width;
            audio.currentTime = pct * audio.duration;
            updateProgress();
            syncTextHighlight();
        }}
        
        function toggleFollow() {{
            autoFollow = document.getElementById('followSwitch').checked;
        }}
        
        function downloadAudio() {{
            if (!audioUrl) return;
            const btnText = document.querySelector('.download-btn span');
            const oldText = btnText.innerText;
            btnText.innerText = '下载中...';
            
            fetch(audioUrl)
                .then(res => res.blob())
                .then(blob => {{
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'podcast_audio.wav';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    btnText.innerText = oldText;
                }})
                .catch(err => {{
                    console.error('Download failed:', err);
                    btnText.innerText = '下载失败';
                    setTimeout(() => btnText.innerText = oldText, 2000);
                    // 降级：直接带上 attname 参数在新窗口打开让浏览器处理下载
                    const fallbackUrl = audioUrl.includes('?') ? audioUrl + '&attname=podcast_audio.wav' : audioUrl + '?attname=podcast_audio.wav';
                    window.open(fallbackUrl, '_blank');
                }});
        }}
        
        function syncTextHighlight() {{
            if (!audio || !audio.duration) return;
            const cur = audio.currentTime;
            const dur = audio.duration;
            const ratio = cur / dur;
            
            const targetCharIdx = ratio * totalLength;
            
            let activeIdx = 0;
            for (let i = 0; i < cumulativeLengths.length; i++) {{
                if (targetCharIdx <= cumulativeLengths[i]) {{
                    activeIdx = i;
                    break;
                }}
            }}
            
            highlightCard(activeIdx);
        }}
        
        function highlightCard(idx) {{
            cards.forEach((card, i) => {{
                if (i === idx) {{
                    if (!card.classList.contains('active')) {{
                        card.classList.add('active');
                        if (autoFollow) {{
                            card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        }}
                    }}
                }} else {{
                    card.classList.remove('active');
                }}
            }});
        }}
        
        function playCard(idx) {{
            if (!audio) return;
            const prevChars = idx > 0 ? cumulativeLengths[idx - 1] : 0;
            const pct = prevChars / totalLength;
            audio.currentTime = pct * audio.duration;
            if (!isPlaying) {{
                audio.play().catch(e => console.log(e));
                isPlaying = true;
                updatePlayerState();
            }}
            highlightCard(idx);
        }}
    </script>
</body>
</html>"""
            generated["content"] = html_content
        else:
            generated["content"] = result.get("content", "")

        # 保留 metadata（如果有）
        if result.get("metadata"):
            generated["metadata"] = result["metadata"]

        logger.info(f"  [类型资源生成] 生成完成!")
        logger.info(f"    标题: {generated['title']}")
        logger.info(f"    类型: {resource_type}")
        logger.info(f"    内容长度: {len(generated['content'])} 字符")
        logger.info(f"{'='*60}")

        return {
            "generated_content": generated,
            "current_step": f"类型资源生成: 已生成 {resource_type} 类型资源「{generated['title']}」",
            "stream_events": [{
                "event_type": "resource_type_generated",
                "agent": "resource_type_generator",
                "data": generated,
                "step_description": f"已生成 {resource_type} 类型资源",
            }],
        }

    except Exception as e:
        logger.error(f"  [类型资源生成] 生成失败: {str(e)}")
        logger.info(f"{'='*60}")
        return {
            "error": f"{resource_type} 资源生成失败: {str(e)}",
            "current_step": f"类型资源生成: 生成失败 - {str(e)[:100]}",
            "stream_events": [{
                "event_type": "error",
                "agent": "resource_type_generator",
                "data": {"error": str(e)},
                "step_description": f"{resource_type} 资源生成失败",
            }],
        }
