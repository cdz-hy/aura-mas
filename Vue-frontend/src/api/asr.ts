/**
 * 语音识别 API - 调用 MiMo-V2.5-ASR 将用户语音转为文本
 */
import { PYTHON_AI_BASE } from './request'

/**
 * 将音频 base64 发送到后端 ASR 端点，通过 SSE 流式接收识别文本
 */
export async function transcribeAudio(
  audioBase64: string,
  format: 'wav' | 'mp3' | 'ogg' = 'ogg',
  language: 'zh' | 'en' | 'auto' = 'zh',
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): Promise<void> {
  try {
    const resp = await fetch(`${PYTHON_AI_BASE}/api/ai/asr/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio: audioBase64, format, language }),
    })

    if (!resp.ok) {
      onError(`ASR 请求失败: ${resp.status}`)
      return
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      onError('无法读取响应流')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''  // 最后一个可能不完整，留到下次

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'chunk' && data.text) {
            onChunk(data.text)
          } else if (data.type === 'done') {
            onDone()
            return
          } else if (data.type === 'error') {
            onError(data.text || '识别失败')
            return
          }
        } catch {
          // 忽略解析错误
        }
      }
    }

    // 流结束但没收到 done 事件
    onDone()
  } catch (e: any) {
    onError(e.message || '网络错误')
  }
}
