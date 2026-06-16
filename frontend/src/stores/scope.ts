import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { generateScope, resumeScope, startScope } from '../api'
import type { GenerationResult, PickPrompt, StudyScope } from '../types'

/** Which screen the scope builder is showing. */
export type ScopePhase = 'intro' | 'picking' | 'done' | 'generated'

/** One resolved step in the scoping trail, kept for the breadcrumb. */
export interface ScopeStep {
  depth: number
  /** Labels the user kept at this frontier. */
  kept: string[]
  /** Label drilled into, if any. */
  drilledInto: string | null
}

/**
 * Drives the interactive topic-scoping flow (Phase 1 of the generator). Mirrors
 * the backend LangGraph session: start a topic, answer successive pick prompts
 * (optionally drilling deeper), until a `StudyScope` comes back. Ephemeral.
 */
export const useScopeStore = defineStore('scope', () => {
  const phase = ref<ScopePhase>('intro')
  const rootTopic = ref('')
  const threadId = ref<string | null>(null)
  /** The current pick prompt to render, or null outside the picking phase. */
  const prompt = ref<PickPrompt | null>(null)
  /** The assembled scope, set once the flow finishes. */
  const scope = ref<StudyScope | null>(null)
  /** Generation summary, set once questions are written. */
  const generation = ref<GenerationResult | null>(null)
  /** Resolved frontiers so far, for the trail/breadcrumb. */
  const trail = ref<ScopeStep[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isBusy = computed(() => loading.value)

  /** Apply a scoping response, switching to the right phase. */
  function apply(state: {
    thread_id: string
    status: string
    pick: PickPrompt | null
    scope: StudyScope | null
  }): void {
    threadId.value = state.thread_id
    if (state.status === 'done') {
      scope.value = state.scope
      prompt.value = null
      phase.value = 'done'
    } else {
      prompt.value = state.pick
      phase.value = 'picking'
    }
  }

  /**
   * Begin scoping a broad topic.
   *
   * @param topic - The broad topic to narrow.
   */
  async function begin(topic: string): Promise<void> {
    loading.value = true
    error.value = null
    rootTopic.value = topic
    trail.value = []
    try {
      apply(await startScope(topic))
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start scoping'
    } finally {
      loading.value = false
    }
  }

  /**
   * Submit the current pick and advance the flow.
   *
   * @param selected - Ids kept at this frontier.
   * @param deeperInto - Id to drill into, or null to finish this branch.
   */
  async function submitPick(selected: string[], deeperInto: string | null): Promise<void> {
    if (!threadId.value || !prompt.value) return
    const labelOf = (id: string) => prompt.value?.options.find((o) => o.id === id)?.label ?? id
    const step: ScopeStep = {
      depth: prompt.value.depth,
      kept: selected.filter((id) => id !== deeperInto).map(labelOf),
      drilledInto: deeperInto ? labelOf(deeperInto) : null,
    }
    loading.value = true
    error.value = null
    try {
      apply(await resumeScope(threadId.value, selected, deeperInto))
      trail.value.push(step)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to submit pick'
    } finally {
      loading.value = false
    }
  }

  /**
   * Generate questions from the finished scope and persist them to disk.
   * Only valid once the flow has reached the `done` phase.
   */
  async function generate(): Promise<void> {
    if (!threadId.value || phase.value !== 'done') return
    loading.value = true
    error.value = null
    try {
      generation.value = await generateScope(threadId.value)
      phase.value = 'generated'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate questions'
    } finally {
      loading.value = false
    }
  }

  /** Clear all scoping state and return to the intro. */
  function reset(): void {
    phase.value = 'intro'
    rootTopic.value = ''
    threadId.value = null
    prompt.value = null
    scope.value = null
    generation.value = null
    trail.value = []
    error.value = null
  }

  return {
    phase,
    rootTopic,
    threadId,
    prompt,
    scope,
    generation,
    trail,
    loading,
    error,
    isBusy,
    begin,
    submitPick,
    generate,
    reset,
  }
})
