import { describe, expect, it } from 'vitest'
import type { Question } from '../types'
import { shuffleQuestion } from './shuffle'

/** Builds a question with sensible defaults for the parts a test doesn't care about. */
function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    id: 'q1',
    topic: 'topic',
    question: 'Which one?',
    options: ['A', 'B', 'C', 'D'],
    correct: 2,
    ...overrides,
  }
}

describe('shuffleQuestion', () => {
  it('remaps correct to the same option text after shuffling', () => {
    const q = makeQuestion({ options: ['A', 'B', 'C', 'D'], correct: 2 })

    const result = shuffleQuestion(q, () => [2, 0, 3, 1])

    expect(result.options[result.correct]).toBe(q.options[q.correct])
  })

  it('order[j] maps each display position back to its original index', () => {
    const q = makeQuestion({ options: ['A', 'B', 'C', 'D'], correct: 0 })

    const result = shuffleQuestion(q, () => [2, 0, 3, 1])

    for (let j = 0; j < result.options.length; j++) {
      expect(result.options[j]).toBe(q.options[result.order[j]])
    }
  })

  it('applies the injected permutation exactly', () => {
    const q = makeQuestion({ options: ['A', 'B', 'C', 'D'], correct: 2 })

    const result = shuffleQuestion(q, () => [2, 0, 3, 1])

    expect(result.order).toEqual([2, 0, 3, 1])
    expect(result.options).toEqual(['C', 'A', 'D', 'B'])
    expect(result.correct).toBe(0)
  })

  it('does not mutate the input question or its arrays', () => {
    const options = ['A', 'B', 'C', 'D']
    const q = makeQuestion({ options, correct: 2 })

    shuffleQuestion(q, () => [3, 2, 1, 0])

    expect(q.options).toBe(options)
    expect(q.options).toEqual(['A', 'B', 'C', 'D'])
    expect(q.correct).toBe(2)
  })

  it('stays correct with duplicate option text (order-based, not text-based)', () => {
    // Two options share the text 'Yes'. A text-based remap could pick the wrong
    // index; the order-based remap must track the originally-correct position.
    const q = makeQuestion({ options: ['Yes', 'No', 'Yes', 'Maybe'], correct: 2 })

    const result = shuffleQuestion(q, () => [0, 2, 1, 3])

    // Display position 1 holds original index 2 — the correct one.
    expect(result.correct).toBe(1)
    expect(result.order[result.correct]).toBe(q.correct)
    expect(result.options[result.correct]).toBe('Yes')
  })
})
