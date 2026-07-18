export interface ChatSession {
  sessionId: string
  intentType: 'profile' | 'chat'
  planId?: number
  title: string
  createdAt: string
  lastMessageAt: string
  messageCount: number
}

export interface ChatMessage {
  id: number
  sessionId: string
  dialogueType: 'USER' | 'AI'
  conversationText: string
  dialogueTime: string
  intentType?: string
  planId?: number
  conversationContext?: string
}
