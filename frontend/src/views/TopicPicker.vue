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
/** The topic the player has selected but not yet started, or null. */
const selectedTopic = ref<string | null>(null)

onMounted(async () => {
  try {
    topics.value = await fetchTopics()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load topics'
  }
})

/** Highlight a topic as the active selection. */
function select(topic: string): void {
  selectedTopic.value = topic
}

/** Start a quiz for the selected topic, applying the optional count. */
async function start(): Promise<void> {
  if (!selectedTopic.value) return
  try {
    await store.startQuiz(selectedTopic.value, count.value ?? undefined)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to start quiz'
  }
}
</script>

<template>
  <section class="card" aria-label="Topic picker">
    <p class="eyebrow">Interview Prep</p>
    <h1>Pick a topic</h1>
    <p class="subhead">Choose a subject and we'll build your quiz.</p>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else>
      <div class="field">
        <label for="qcount">
          Number of questions <span class="hint">(blank = all)</span>
        </label>
        <input
          id="qcount"
          v-model.number="count"
          type="number"
          min="1"
          placeholder="all"
          inputmode="numeric"
        />
      </div>

      <div class="topic-list" role="listbox" aria-label="Topics">
        <button
          v-for="t in topics"
          :key="t.topic"
          class="topic"
          :class="{ selected: selectedTopic === t.topic }"
          role="option"
          :aria-selected="selectedTopic === t.topic"
          @click="select(t.topic)"
        >
          <span class="check" aria-hidden="true">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <path
                d="M3 8.5l3.2 3.2L13 4.5"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span class="topic-name">{{ t.topic }}</span>
          <span class="topic-count">{{ t.count }}</span>
        </button>
      </div>

      <button
        class="btn btn-primary btn-block"
        :disabled="!selectedTopic"
        @click="start"
      >
        Start quiz
      </button>
    </template>
  </section>
</template>
