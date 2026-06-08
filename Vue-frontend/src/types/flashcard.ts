export interface Flashcard {
  id: number
  noteId: number
  userId: number
  question: string
  answer: string
  difficulty: number
  easeFactor: number
  reviewInterval: number
  reviewCount: number
  nextReviewAt: string | null
  createdAt: string
}

export interface FlashcardSaveRequest {
  noteId: number
  cards: {
    question: string
    answer: string
    difficulty: number
  }[]
}
