<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchQuiz } from '../api'
import type { Question } from '../types'

const question = ref<Question | null>(null)
const selected = ref<number | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const questions = await fetchQuiz('python')
    question.value = questions[0] ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load quiz'
  }
})

/** Record the user's choice. Grading happens at display time. */
function choose(index: number): void {
  if (selected.value === null) {
    selected.value = index
  }
}
</script>

<template>
  <main>
    <p v-if="error">{{ error }}</p>
    <p v-else-if="!question">Loading…</p>
    <section v-else>
      <h2>{{ question.question }}</h2>
      <ul>
        <li v-for="(option, i) in question.options" :key="i">
          <button :disabled="selected !== null" @click="choose(i)">
            {{ option }}
          </button>
        </li>
      </ul>

      <div v-if="selected !== null">
        <p>{{ selected === question.correct ? 'Correct!' : 'Incorrect.' }}</p>
        <p v-if="question.explanation">{{ question.explanation }}</p>
      </div>
    </section>
  </main>
</template>
