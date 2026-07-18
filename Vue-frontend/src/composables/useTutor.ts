import { ref, computed, watch, onUnmounted, type ComputedRef } from 'vue'
import { useTutorStore, type TutorMessage } from '@/stores/tutorStore'

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

  // 组件级别的 messages 快照，避免不同 planId 的 tutor 实例互相覆盖
  const localMessages = ref<TutorMessage[]>([])

  // 判断 store 当前是否属于本组件的 context
  function isMyContext(): boolean {
    return store.contextPlanId === context.value.planId
  }

  // 同步：当 store 切换到本组件的 planId 时，把 store messages 拷贝到 local
  watch(() => store.contextPlanId, () => {
    if (isMyContext()) {
      localMessages.value = [...store.messages]
    }
  })

  // 同步：store messages 发生变化且属于本组件时，更新 local
  // 使用深度监听以捕获 SSE 流式内容更新（就地修改最后一条消息）
  watch(() => store.messages, () => {
    if (isMyContext()) {
      localMessages.value = [...store.messages]
    }
  }, { deep: true })

  // Sync context to store and load sessions
  watch(context, (ctx) => {
    store.setPlanContext(ctx.planId, ctx.resourceId)
    store.loadSessions()
    // setPlanContext 可能恢复了缓存的 messages
    if (isMyContext()) {
      localMessages.value = [...store.messages]
    }
  }, { immediate: true })

  // Cleanup on unmount
  onUnmounted(() => {
    store.closeConnection()
  })

  const followUp = computed(() => pickFollowUp())

  return {
    messages: localMessages,
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
    setPageContext: (type: string, data: Record<string, any>) => store.setPageContext(type, data),
    deleteMessage: (id: number) => store.deleteMessage(id),
    deleteMessages: (ids: number[]) => store.deleteMessages(ids),
  }
}
