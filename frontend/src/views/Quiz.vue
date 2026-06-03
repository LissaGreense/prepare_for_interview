<script setup lang="ts">
import { computed } from 'vue'
import { useQuizStore } from '../stores/quiz'

const store = useQuizStore()

/** The question currently being answered. */
const question = computed(() => store.questions[store.currentIndex])
/** The recorded answer for the current question, or `null` if unanswered. */
const answer = computed(() => store.answers[store.currentIndex] ?? null)
/** Whether the current question has been answered. */
const answered = computed(() => answer.value !== null)
/** Whether the current question is the last in the run. */
const isLast = computed(() => store.currentIndex === store.questions.length - 1)

/**
 * Record the chosen option. Display order matches original order today; the
 * shuffle task translates clicked positions back to original before this call.
 */
function choose(originalOptionIndex: number): void {
  store.recordAnswer(originalOptionIndex)
}
</script>

<template>
  <main>
    <section v-if="question">
      <p>Question {{ store.currentIndex + 1 }} of {{ store.questions.length }}</p>
      <h2>{{ question.question }}</h2>
      <ul>
        <li v-for="(option, i) in question.options" :key="i">
          <button :disabled="answered" @click="choose(i)">{{ option }}</button>
        </li>
      </ul>

      <div v-if="answered">
        <p>{{ answer === question.correct ? 'Correct!' : 'Incorrect.' }}</p>
        <p v-if="question.explanation">{{ question.explanation }}</p>
        <button @click="store.next()">{{ isLast ? 'See results' : 'Next' }}</button>
      </div>
    </section>
  </main>
</template>
