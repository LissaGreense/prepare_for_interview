import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import type { Question } from '../types'
import { useQuizStore } from './quiz'

/** Builds a question whose correct answer is `correct` (defaults to index 0). */
function makeQuestion(id: string, correct = 0): Question {
  return {
    id,
    topic: 'topic',
    question: `Question ${id}`,
    options: ['A', 'B', 'C', 'D'],
    correct,
  }
}

describe('quiz store score', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('counts every question when all answers are correct', () => {
    const store = useQuizStore()
    store.questions = [makeQuestion('a', 0), makeQuestion('b', 1), makeQuestion('c', 2)]
    store.answers = [0, 1, 2]

    expect(store.score).toBe(3)
  })

  it('is zero when every answer is wrong', () => {
    const store = useQuizStore()
    store.questions = [makeQuestion('a', 0), makeQuestion('b', 1), makeQuestion('c', 2)]
    store.answers = [1, 0, 0]

    expect(store.score).toBe(0)
  })

  it('counts only the correct answers in a mixed set', () => {
    const store = useQuizStore()
    store.questions = [makeQuestion('a', 0), makeQuestion('b', 1), makeQuestion('c', 2)]
    store.answers = [0, 3, 2] // first and third correct, second wrong

    expect(store.score).toBe(2)
  })

  it('treats unanswered (null) entries as wrong', () => {
    const store = useQuizStore()
    store.questions = [makeQuestion('a', 0), makeQuestion('b', 1), makeQuestion('c', 2)]
    store.answers = [0, null, null] // only the first is answered, correctly

    expect(store.score).toBe(1)
  })
})
