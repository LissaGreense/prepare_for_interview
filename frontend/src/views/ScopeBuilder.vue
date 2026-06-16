<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useScopeStore } from '../stores/scope'

const store = useScopeStore()

/** Broad topic typed on the intro screen. */
const topic = ref('')
/** Ids the user has checked to keep at the current frontier. */
const selected = ref<string[]>([])
/** Id the user chose to drill deeper into, or null. */
const drillInto = ref<string | null>(null)

// Reset the local pick whenever a new frontier arrives.
watch(
  () => store.prompt,
  () => {
    selected.value = []
    drillInto.value = null
  },
)

/** Toggle an option in/out of the kept set. */
function toggle(id: string): void {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((x) => x !== id)
    : [...selected.value, id]
}

/** Choosing "drill into X" again clears it (acts as a toggle). */
function setDrill(id: string): void {
  drillInto.value = drillInto.value === id ? null : id
}

const canSubmit = computed(
  () => !store.loading && (selected.value.length > 0 || drillInto.value !== null),
)

const continueLabel = computed(() => {
  if (drillInto.value) {
    const o = store.prompt?.options.find((x) => x.id === drillInto.value)
    return `Drill into ${o?.label ?? 'topic'} →`
  }
  const keepers = selected.value.filter((id) => id !== drillInto.value).length
  return `Build scope (${keepers} topic${keepers === 1 ? '' : 's'})`
})

async function onBegin(): Promise<void> {
  if (!topic.value.trim()) return
  await store.begin(topic.value.trim())
}

async function onContinue(): Promise<void> {
  await store.submitPick([...selected.value], drillInto.value)
}
</script>

<template>
  <section class="card" aria-label="Question generator">
    <p class="eyebrow">AI Generator</p>

    <!-- Intro: enter a broad topic -->
    <template v-if="store.phase === 'intro'">
      <h1>Scope a topic</h1>
      <p class="subhead">
        Name a broad area. We'll research it, you pick what to cover, and we'll gather docs to
        generate questions from.
      </p>
      <form @submit.prevent="onBegin">
        <input
          v-model="topic"
          class="scope-input"
          type="text"
          placeholder="e.g. web development, distributed systems, React"
          :disabled="store.loading"
          aria-label="Broad topic"
        />
        <button class="btn btn-primary btn-block" :disabled="!topic.trim() || store.loading">
          {{ store.loading ? 'Researching…' : 'Start' }}
        </button>
      </form>
    </template>

    <!-- Picking: choose subtopics, optionally drill deeper -->
    <template v-else-if="store.phase === 'picking' && store.prompt">
      <h1>{{ store.rootTopic }}</h1>
      <p v-if="store.trail.length" class="scope-trail">
        <span v-for="(step, i) in store.trail" :key="i">
          {{ step.drilledInto ? `↳ ${step.drilledInto}` : step.kept.join(', ') }}
        </span>
      </p>
      <p class="subhead">{{ store.prompt.question }}</p>

      <div class="scope-options" role="group" aria-label="Topics">
        <div v-for="o in store.prompt.options" :key="o.id" class="scope-option-row">
          <button
            type="button"
            class="scope-option"
            :class="{ kept: selected.includes(o.id) }"
            :aria-pressed="selected.includes(o.id)"
            @click="toggle(o.id)"
          >
            <span class="scope-option__check" aria-hidden="true">✓</span>
            <span class="scope-option__label">{{ o.label }}</span>
            <span class="scope-option__kind">{{ o.kind }}</span>
          </button>
          <button
            v-if="store.prompt.can_deepen"
            type="button"
            class="scope-drill"
            :class="{ active: drillInto === o.id }"
            :title="`Drill deeper into ${o.label}`"
            @click="setDrill(o.id)"
          >
            ↳ deeper
          </button>
        </div>
      </div>

      <p v-if="store.error" class="error" role="alert">{{ store.error }}</p>

      <div class="scope-actions">
        <button class="btn btn-primary" :disabled="!canSubmit" @click="onContinue">
          {{ store.loading ? 'Working…' : continueLabel }}
        </button>
        <button class="btn btn-ghost" :disabled="store.loading" @click="store.reset()">Quit</button>
      </div>
    </template>

    <!-- Done: show the assembled scope -->
    <template v-else-if="store.phase === 'done' && store.scope">
      <h1>Scope ready</h1>
      <p class="subhead">
        {{ store.scope.topics.length }} topic{{
          store.scope.topics.length === 1 ? '' : 's'
        }}
        gathered for <strong>{{ store.scope.root_topic }}</strong
        >. This feeds question generation next.
      </p>

      <p v-if="!store.scope.topics.length" class="error">
        Nothing was selected — start over and keep at least one topic.
      </p>

      <div class="scope-result">
        <details v-for="t in store.scope.topics" :key="t.id" class="scope-doc">
          <summary>
            <span class="scope-doc__label">{{ t.label }}</span>
            <span class="scope-doc__meta">{{ t.doc_text.length }} chars</span>
          </summary>
          <ul v-if="t.sources.length" class="scope-doc__sources">
            <li v-for="s in t.sources" :key="s">
              <a :href="s" target="_blank" rel="noopener noreferrer">{{ s }}</a>
            </li>
          </ul>
          <pre class="scope-doc__text"
            >{{ t.doc_text.slice(0, 800) }}{{ t.doc_text.length > 800 ? '…' : '' }}</pre
          >
        </details>
      </div>

      <p v-if="store.error" class="error" role="alert">{{ store.error }}</p>

      <div class="scope-actions">
        <button
          class="btn btn-primary"
          :disabled="store.loading || !store.scope.topics.length"
          @click="store.generate()"
        >
          {{ store.loading ? 'Generating…' : 'Generate questions' }}
        </button>
        <button class="btn btn-ghost" :disabled="store.loading" @click="store.reset()">
          Scope another topic
        </button>
      </div>
    </template>

    <!-- Generated: questions written to disk -->
    <template v-else-if="store.phase === 'generated' && store.generation">
      <h1>Questions generated</h1>
      <p class="subhead">
        Wrote <strong>{{ store.generation.total }}</strong> question{{
          store.generation.total === 1 ? '' : 's'
        }}
        for <strong>{{ store.generation.root_topic }}</strong> to your question bank.
      </p>

      <ul class="scope-result">
        <li v-for="t in store.generation.topics" :key="t.topic_id" class="scope-gen-row">
          <span class="scope-doc__label">{{ t.label }}</span>
          <span class="scope-doc__meta">{{ t.written }} written</span>
        </li>
      </ul>

      <button class="btn btn-primary btn-block" @click="store.reset()">Scope another topic</button>
    </template>
  </section>
</template>
