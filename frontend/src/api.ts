import type { Question, Topic } from './types'

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
