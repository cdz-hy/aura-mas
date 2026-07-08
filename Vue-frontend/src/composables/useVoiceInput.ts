/**
 * 语音输入 composable - 使用浏览器内置 Web Speech API 进行语音识别
 *
 * 用法：
 *   const { isRecording, toggle } = useVoiceInput({
 *     onText: (text) => inputText.value += text,
 *     onError: (err) => showToast(err, 'error'),
 *   })
 */
import { ref } from 'vue'

export interface UseVoiceInputOptions {
  /** 识别到文字时回调（最终结果） */
  onText: (text: string) => void
  onError: (err: string) => void
}

export function useVoiceInput(options: UseVoiceInputOptions) {
  const isRecording = ref(false)
  const error = ref('')

  let recognition: any = null

  function startRecording() {
    error.value = ''
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      const msg = '当前浏览器不支持语音识别，请使用 Chrome 或 Edge'
      error.value = msg
      options.onError(msg)
      return
    }

    recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = true          // 持续识别，不自动停止
    recognition.interimResults = true      // 返回中间结果
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      let finalText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalText += event.results[i][0].transcript
        }
      }
      if (finalText) {
        options.onText(finalText)
      }
    }

    recognition.onerror = (event: any) => {
      if (event.error === 'no-speech') {
        return
      }
      const errMap: Record<string, string> = {
        'not-allowed': '请允许麦克风权限后再试',
        'audio-capture': '未检测到麦克风设备',
        'network': '语音识别网络错误',
        'aborted': '语音识别已取消',
      }
      const msg = errMap[event.error] || `语音识别错误: ${event.error}`
      error.value = msg
      options.onError(msg)
    }

    recognition.onend = () => {
      isRecording.value = false
    }

    try {
      recognition.start()
      isRecording.value = true
    } catch (e: any) {
      options.onError(`启动语音识别失败: ${e.message}`)
    }
  }

  function stopRecording() {
    if (recognition) {
      recognition.stop()
      recognition = null
      isRecording.value = false
    }
  }

  function toggle() {
    if (isRecording.value) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return {
    isRecording,
    error,
    startRecording,
    stopRecording,
    toggle,
  }
}
