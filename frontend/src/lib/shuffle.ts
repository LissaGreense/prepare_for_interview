import type { Question } from '../types'

/**
 * Produces a permutation of the indices `[0, 1, ..., n-1]`. Injected into
 * {@link shuffleQuestion} so tests can drive a deterministic order.
 */
export type Permute = (n: number) => number[]

/** A question's options reordered for display, with the remap back to original. */
export interface ShuffledQuestion {
  /** The options in display order — a permutation of the question's `options`. */
  options: string[]
  /** Index, within `options`, of the originally-correct option. */
  correct: number
  /** `order[j]` is the ORIGINAL option index shown at display position `j`. */
  order: number[]
}

/**
 * Fisher–Yates shuffle of `[0, ..., n-1]` using `Math.random`. The default
 * source of randomness for {@link shuffleQuestion}.
 *
 * @param n - Number of indices to permute.
 * @returns A uniformly-random permutation of `[0, ..., n-1]`.
 */
function fisherYates(n: number): number[] {
  const order = Array.from({ length: n }, (_, i) => i)
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[order[i], order[j]] = [order[j], order[i]]
  }
  return order
}

/**
 * Reorder a question's options for display while tracking the correct answer
 * through the shuffle. Pure: the input question and its arrays are never
 * mutated. View-only — the stored question stays canonical in original-index
 * space.
 *
 * @param q - The question whose options to shuffle.
 * @param permute - Source of the permutation; defaults to a real Fisher–Yates
 *   shuffle. Inject a fixed permutation (e.g. `() => [2, 0, 3, 1]`) to test
 *   deterministically.
 * @returns The display-ordered options, the correct option's new index, and the
 *   `order` map from display position back to original option index.
 */
export function shuffleQuestion(q: Question, permute: Permute = fisherYates): ShuffledQuestion {
  const order = permute(q.options.length)
  const options = order.map((i) => q.options[i])
  const correct = order.indexOf(q.correct)
  return { options, correct, order }
}
