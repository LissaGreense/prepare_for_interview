<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { useQuizStore } from './stores/quiz'
import type { View } from './stores/quiz'
import TopicPicker from './views/TopicPicker.vue'
import Quiz from './views/Quiz.vue'
import Results from './views/Results.vue'
import ScopeBuilder from './views/ScopeBuilder.vue'

const store = useQuizStore()

/** Top-level mode: take a quiz, or generate new questions with AI. */
const mode = ref<'quiz' | 'generate'>('quiz')

/** Maps each quiz-flow view to the component that renders it. */
const quizViews: Record<View, Component> = {
  picker: TopicPicker,
  quiz: Quiz,
  results: Results,
}

const current = computed<Component>(() =>
  mode.value === 'generate' ? ScopeBuilder : quizViews[store.view],
)
</script>

<template>
  <nav class="app-nav" aria-label="Mode">
    <button
      class="app-nav__tab"
      :class="{ active: mode === 'quiz' }"
      :aria-pressed="mode === 'quiz'"
      @click="mode = 'quiz'"
    >
      Quiz
    </button>
    <button
      class="app-nav__tab"
      :class="{ active: mode === 'generate' }"
      :aria-pressed="mode === 'generate'"
      @click="mode = 'generate'"
    >
      ✨ Generate
    </button>
  </nav>
  <component :is="current" />
</template>
