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
  <section class="card" aria-label="Results">
    <div class="score-block">
      <div class="score-eyebrow">Your score</div>
      <div class="score-number">
        <span class="got">{{ store.score }}</span>
        <span class="of">/ {{ store.questions.length }}</span>
      </div>
      <p v-if="missed.length" class="score-sub">{{ missed.length }} to review below.</p>
      <p v-else class="score-sub">Perfect score — nothing to review.</p>
    </div>

    <template v-if="missed.length">
      <p class="review-title">Review — {{ missed.length }} missed</p>
      <div class="review-list">
        <article v-for="m in missed" :key="m.id" class="review-item">
          <h3 class="review-q">{{ m.question }}</h3>
          <div class="answer-line yours">
            <span class="key">Your answer</span>
            <span class="val">{{ m.chosen ?? 'No answer' }}</span>
          </div>
          <div class="answer-line correct">
            <span class="key">Correct</span>
            <span class="val">{{ m.correct }}</span>
          </div>
          <p v-if="m.explanation" class="review-exp">{{ m.explanation }}</p>
        </article>
      </div>
    </template>

    <button class="btn btn-ghost btn-block" @click="store.reset()">Pick another topic</button>
  </section>
</template>
