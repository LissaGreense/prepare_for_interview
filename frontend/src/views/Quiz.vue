<script setup lang="ts">
import { computed } from 'vue'
import { useQuizStore } from '../stores/quiz'
import { shuffleQuestion } from '../lib/shuffle'

const store = useQuizStore()

/** The question currently being answered. */
const question = computed(() => store.questions[store.currentIndex])
/**
 * The current question's options in shuffled display order, with the remap back
 * to original indices. Computed once per question: a Vue `computed` only
 * re-evaluates when a reactive dependency it read changes — here only
 * `question` — so answering (which mutates `store.answers`) does NOT reshuffle.
 */
const shuffled = computed(() => (question.value ? shuffleQuestion(question.value) : null))
/** The recorded answer for the current question, or `null` if unanswered. */
const answer = computed(() => store.answers[store.currentIndex] ?? null)
/** Whether the current question has been answered. */
const answered = computed(() => answer.value !== null)
/** Whether the current question is the last in the run. */
const isLast = computed(() => store.currentIndex === store.questions.length - 1)

/**
 * Record the option at shuffled display position `displayIndex`, translating it
 * back to its original option index before handing it to the store (which stays
 * in original-index space).
 *
 * @param displayIndex - Position of the clicked option in the shuffled list.
 */
function choose(displayIndex: number): void {
  if (!shuffled.value) return
  store.recordAnswer(shuffled.value.order[displayIndex])
}
</script>

<template>
  <main>
    <section v-if="question && shuffled">
      <p>Question {{ store.currentIndex + 1 }} of {{ store.questions.length }}</p>
      <h2>{{ question.question }}</h2>
      <ul>
        <li v-for="(option, i) in shuffled.options" :key="i">
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
