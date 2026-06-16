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

// --- AI question generator, Phase 1: interactive topic scoping ---

/** One selectable topic at the current frontier. */
export interface PickOption {
  id: string
  label: string
  /** 'technology' for a named tool/framework, else 'subtopic'. */
  kind: string
}

/** What to render when the scoping graph pauses for a human pick. */
export interface PickPrompt {
  question: string
  /** Current deepen level (0 at the root frontier). */
  depth: number
  /** Whether the user may still drill deeper from here. */
  can_deepen: boolean
  options: PickOption[]
}

/** A selected leaf topic plus the documentation gathered for it. */
export interface ScopeTopic {
  id: string
  label: string
  doc_text: string
  sources: string[]
}

/** Phase-1 output: the curated leaves + their docs. */
export interface StudyScope {
  root_topic: string
  topics: ScopeTopic[]
}

/**
 * Discriminated scoping response: either awaiting the next pick, or done with
 * the assembled scope.
 */
export interface ScopeState {
  status: 'awaiting_pick' | 'done'
  thread_id: string
  pick: PickPrompt | null
  scope: StudyScope | null
}

// --- AI question generator, Phase 2: generation ---

/** How many questions were written for one scoped topic. */
export interface TopicGeneration {
  topic_id: string
  label: string
  /** Count of valid questions written to disk for this topic. */
  written: number
}

/** Summary of a generation run, from `POST /scope/{id}/generate`. */
export interface GenerationResult {
  thread_id: string
  root_topic: string
  topics: TopicGeneration[]
  /** Total questions written across all topics. */
  total: number
}
