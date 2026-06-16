import type { GenerationResult, Question, ScopeState, Topic } from './types'

/** Backend base URL (FastAPI dev server). */
const API_BASE = 'http://localhost:8000'

/**
 * Fetch the list of available topics with their question counts.
 *
 * @returns The available topics.
 * @throws If the request fails or the backend returns a non-2xx status.
 */
export async function fetchTopics(): Promise<Topic[]> {
  const res = await fetch(`${API_BASE}/topics`)
  if (!res.ok) {
    throw new Error(`Failed to load topics: ${res.status}`)
  }
  return (await res.json()) as Topic[]
}

/**
 * Fetch questions for a topic from the backend.
 *
 * @param topic - Topic name (e.g. "python").
 * @returns The topic's questions, randomized server-side.
 * @throws If the request fails or the backend returns a non-2xx status.
 */
export async function fetchQuiz(topic: string): Promise<Question[]> {
  const res = await fetch(`${API_BASE}/quiz?topic=${encodeURIComponent(topic)}`)
  if (!res.ok) {
    throw new Error(`Failed to load quiz for "${topic}": ${res.status}`)
  }
  return (await res.json()) as Question[]
}

/**
 * Begin scoping a broad topic. Returns the first pick prompt the user answers.
 *
 * @param rootTopic - The broad topic to narrow, e.g. "web development".
 * @returns The scoping state (awaiting the first pick).
 * @throws If the request fails or the backend returns a non-2xx status.
 */
export async function startScope(rootTopic: string): Promise<ScopeState> {
  const res = await fetch(`${API_BASE}/scope/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ root_topic: rootTopic }),
  })
  if (!res.ok) {
    throw new Error(`Failed to start scoping: ${res.status}`)
  }
  return (await res.json()) as ScopeState
}

/**
 * Resume a scoping session with the user's pick.
 *
 * @param threadId - The session id from {@link startScope}.
 * @param selected - Ids of the options the user kept at this frontier.
 * @param deeperInto - Id to drill deeper into, or `null` to finish this branch.
 * @returns The next pick prompt, or the final assembled scope.
 * @throws If the session is unknown (404) or the request otherwise fails.
 */
export async function resumeScope(
  threadId: string,
  selected: string[],
  deeperInto: string | null,
): Promise<ScopeState> {
  const res = await fetch(`${API_BASE}/scope/${encodeURIComponent(threadId)}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected, deeper_into: deeperInto }),
  })
  if (!res.ok) {
    throw new Error(`Failed to resume scoping: ${res.status}`)
  }
  return (await res.json()) as ScopeState
}

/**
 * Generate and persist questions from a finished scope.
 *
 * @param threadId - The session id of a scope that reached `done`.
 * @returns Per-topic written counts.
 * @throws If the scope is unknown (404), not yet finished (409), or the request fails.
 */
export async function generateScope(threadId: string): Promise<GenerationResult> {
  const res = await fetch(`${API_BASE}/scope/${encodeURIComponent(threadId)}/generate`, {
    method: 'POST',
  })
  if (!res.ok) {
    throw new Error(`Failed to generate questions: ${res.status}`)
  }
  return (await res.json()) as GenerationResult
}
