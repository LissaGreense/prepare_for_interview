/** A topic and how many questions it contains, from `GET /topics`. */
export interface Topic {
  topic: string
  count: number
}

/** A single-choice quiz question, mirroring the backend `Question` shape. */
export interface Question {
  id: string
  topic: string
  question: string
  options: string[]
  /** Zero-based index into `options` of the correct answer. */
  correct: number
  explanation?: string
}
