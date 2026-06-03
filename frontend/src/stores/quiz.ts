import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchQuiz } from '../api'
import type { Question } from '../types'

/** Which top-level screen is currently shown. */
export type View = 'picker' | 'quiz' | 'results'

/**
 * In-memory quiz state. Holds the current view and the questions for the
 * active run. Grading and answer tracking land in later tasks; this store
 * currently owns navigation and quiz loading only.
 */
export const useQuizStore = defineStore('quiz', () => {
  /** The screen currently rendered by `App.vue`. */
  const view = ref<View>('picker')
  /** Questions for the active run, set when a quiz starts. */
  const questions = ref<Question[]>([])

  /**
   * Fetch a quiz for the given topic and switch to the quiz view.
   *
   * @param topic - Topic to drill.
   * @param count - Optional number of questions; omitted = all.
   * @throws If the quiz fetch fails (caller handles the error state).
   */
  async function startQuiz(topic: string, count?: number): Promise<void> {
    questions.value = await fetchQuiz(topic, count)
    view.value = 'quiz'
  }

  return { view, questions, startQuiz }
})
