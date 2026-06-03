import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchQuiz } from '../api'
import type { Question } from '../types'

/** Which top-level screen is currently shown. */
export type View = 'picker' | 'quiz' | 'results'

/**
 * In-memory quiz state. Owns navigation, the active question set, the player's
 * answers, and client-side scoring. State is ephemeral — a refresh starts over.
 */
export const useQuizStore = defineStore('quiz', () => {
  /** The screen currently rendered by `App.vue`. */
  const view = ref<View>('picker')
  /** Questions for the active run, set when a quiz starts. */
  const questions = ref<Question[]>([])
  /** Index into `questions` of the question currently being answered. */
  const currentIndex = ref(0)
  /**
   * Recorded answers, parallel to `questions`. Each entry is the chosen
   * ORIGINAL option index (index into `question.options` as stored), or `null`
   * until that question is answered.
   */
  const answers = ref<(number | null)[]>([])

  /** Number of correctly answered questions. */
  const score = computed(
    () => answers.value.filter((a, i) => a === questions.value[i]?.correct).length,
  )

  /**
   * Fetch a quiz for the given topic and switch to the quiz view, resetting
   * progress for the new run.
   *
   * @param topic - Topic to drill.
   * @param count - Optional number of questions; omitted = all.
   * @throws If the quiz fetch fails (caller handles the error state).
   */
  async function startQuiz(topic: string, count?: number): Promise<void> {
    questions.value = await fetchQuiz(topic, count)
    currentIndex.value = 0
    answers.value = questions.value.map(() => null)
    view.value = 'quiz'
  }

  /**
   * Record the player's choice for the current question. The first answer
   * sticks — subsequent calls are ignored.
   *
   * @param originalOptionIndex - Chosen option's index into `question.options`
   *   as stored (callers translate any display-order shuffle back to original).
   */
  function recordAnswer(originalOptionIndex: number): void {
    if (answers.value[currentIndex.value] === null) {
      answers.value[currentIndex.value] = originalOptionIndex
    }
  }

  /** Advance to the next question, or to the results view past the last one. */
  function next(): void {
    if (currentIndex.value >= questions.value.length - 1) {
      view.value = 'results'
    } else {
      currentIndex.value += 1
    }
  }

  /** Clear all run state and return to the topic picker. */
  function reset(): void {
    questions.value = []
    answers.value = []
    currentIndex.value = 0
    view.value = 'picker'
  }

  return {
    view,
    questions,
    currentIndex,
    answers,
    score,
    startQuiz,
    recordAnswer,
    next,
    reset,
  }
})
