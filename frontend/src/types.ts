/** A topic with its display metadata and question count, from `GET /topics`. */
export interface Topic {
  /** Folder name / id used by `GET /quiz`. */
  topic: string
  /** Display name; falls back to `topic` when no manifest provides one. */
  title: string
  /** Optional emoji shown on the topic card. */
  icon?: string
  /** Optional short subtitle shown on the topic card. */
  description?: string
  /** Number of valid questions currently in the topic. */
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
