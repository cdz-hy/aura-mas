import { computed, watch, onUnmounted, type ComputedRef } from 'vue'
import { useTutorStore } from '@/stores/tutorStore'

export interface TutorContext {
  planId: number
  resourceId: number
}

const FOLLOW_UP_TEMPLATES: Record<string, string[]> = {
  quiz: ['测验有没有什么不理解的知识点，我可以帮帮你哦', '测验做得怎么样？有不会的题目吗？'],
  document: ['图文内容有什么不懂的地方吗，我可以教教你哦', '这个知识点理解了吗？'],
  text: ['图文内容有什么不懂的地方吗，我可以教教你哦', '这个知识点理解了吗？'],
  code: ['代码部分有什么疑问吗？', '这段代码能看懂吗？'],
  mindmap: ['思维导图清晰吗？有需要解释的分支吗？'],
  summary: ['总结内容理解了吗？有遗漏的要点吗？'],
  video: ['视频内容有什么不明白的吗？'],
  default: ['有什么不懂的地方吗，我可以帮你哦'],
}

export function pickFollowUp(moduleType?: string): string {
  const templates = FOLLOW_UP_TEMPLATES[moduleType || ''] || FOLLOW_UP_TEMPLATES.default
  return templates[Math.floor(Math.random() * templates.length)]
}

export function useTutor(context: ComputedRef<TutorContext>) {
  const store = useTutorStore()

  // Sync context to store and load sessions
  watch(context, (ctx) => {
    store.setPlanContext(ctx.planId, ctx.resourceId)
    store.loadSessions()
  }, { immediate: true })

  // Cleanup on unmount
  onUnmounted(() => {
    store.closeConnection()
  })

  const followUp = computed(() => pickFollowUp())

  return {
    messages: computed(() => store.messages),
    loading: computed(() => store.loading),
    progress: computed(() => store.progress),
    sessions: computed(() => store.sessions),
    sessionsLoading: computed(() => store.sessionsLoading),
    activeSessionId: computed(() => store.activeSessionId),
    followUp,
    send: (text: string) => store.sendMessage(text),
    newSession: () => store.newSession(),
    selectSession: (id: string) => store.selectSession(id),
    stopGeneration: () => store.stopGeneration(),
    loadSessions: () => store.loadSessions(),
  }
}
