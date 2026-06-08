import { reactive } from 'vue'

export interface ToastItem {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message: string
  duration: number
  progress: number
  exiting: boolean
}

let _nextId = 0

export const toastState = reactive({
  toasts: [] as ToastItem[],
})

export function removeToast(id: number) {
  const idx = toastState.toasts.findIndex(t => t.id === id)
  if (idx === -1) return
  toastState.toasts[idx].exiting = true
  setTimeout(() => {
    const i = toastState.toasts.findIndex(t => t.id === id)
    if (i !== -1) toastState.toasts.splice(i, 1)
  }, 260)
}

export function showToast(
  message: string,
  type: ToastItem['type'] = 'info',
  options?: { title?: string; duration?: number }
) {
  const id = ++_nextId
  const duration = options?.duration ?? 3500

  const toast: ToastItem = {
    id,
    type,
    title: options?.title,
    message,
    duration,
    progress: 100,
    exiting: false,
  }

  toastState.toasts.push(toast)

  // Start progress animation on next frame
  requestAnimationFrame(() => {
    const t = toastState.toasts.find(t => t.id === id)
    if (t) t.progress = 0
  })

  // Auto dismiss
  setTimeout(() => removeToast(id), duration)

  return id
}
