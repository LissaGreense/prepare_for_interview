<script setup lang="ts">
import { computed } from 'vue'
import { useQuizStore } from '../stores/quiz'

const store = useQuizStore()

/** A question the player got wrong, paired with the text we need to review it. */
interface MissedQuestion {
  id: string
  question: string
  /** The player's chosen option text, or null if they left it unanswered. */
  chosen: string | null
  correct: string
  explanation?: string
}

/**
 * The questions the player answered incorrectly (including unanswered ones),
 * resolved to the option text needed to render a review.
 */
const missed = computed<MissedQuestion[]>(() =>
  store.questions
    .map((q, i): MissedQuestion | null => {
      const answer = store.answers[i]
      if (answer === q.correct) return null
      return {
        id: q.id,
        question: q.question,
        chosen: answer === null ? null : q.options[answer],
        correct: q.options[q.correct],
        explanation: q.explanation,
      }
    })
    .filter((m): m is MissedQuestion => m !== null),
)
</script>

<template>
  <main>
    <h1>Results</h1>
    <p>Score: {{ store.score }} / {{ store.questions.length }}</p>

    <section v-if="missed.length">
      <h2>Review</h2>
      <ul>
        <li v-for="m in missed" :key="m.id">
          <p>{{ m.question }}</p>
          <p>Your answer: {{ m.chosen ?? 'No answer' }}</p>
          <p>Correct answer: {{ m.correct }}</p>
          <p v-if="m.explanation">{{ m.explanation }}</p>
        </li>
      </ul>
    </section>
    <p v-else>Perfect score — nothing to review.</p>

    <button @click="store.reset()">Pick another topic</button>
  </main>
</template>
