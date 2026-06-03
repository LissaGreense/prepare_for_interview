<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import { useQuizStore } from './stores/quiz'
import type { View } from './stores/quiz'
import TopicPicker from './views/TopicPicker.vue'
import Quiz from './views/Quiz.vue'
import Results from './views/Results.vue'

const store = useQuizStore()

/** Maps each view to the component that renders it. */
const views: Record<View, Component> = {
  picker: TopicPicker,
  quiz: Quiz,
  results: Results,
}

const current = computed<Component>(() => views[store.view])
</script>

<template>
  <component :is="current" />
</template>
