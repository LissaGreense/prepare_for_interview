<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchTopics } from '../api'
import { useQuizStore } from '../stores/quiz'
import type { Topic } from '../types'

const store = useQuizStore()

const topics = ref<Topic[]>([])
const error = ref<string | null>(null)
/** Optional question count; null = all questions in the topic. */
const count = ref<number | null>(null)

onMounted(async () => {
  try {
    topics.value = await fetchTopics()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load topics'
  }
})

/** Start a quiz for the chosen topic, applying the optional count. */
async function start(topic: string): Promise<void> {
  try {
    await store.startQuiz(topic, count.value ?? undefined)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to start quiz'
  }
}
</script>

<template>
  <main>
    <h1>Pick a topic</h1>
    <p v-if="error">{{ error }}</p>
    <template v-else>
      <label>
        Questions (blank = all):
        <input v-model.number="count" type="number" min="1" />
      </label>
      <ul>
        <li v-for="t in topics" :key="t.topic">
          <button @click="start(t.topic)">{{ t.topic }} ({{ t.count }})</button>
        </li>
      </ul>
    </template>
  </main>
</template>
