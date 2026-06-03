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
/** Whether the recorded answer matches the correct option. */
const isCorrect = computed(() => answer.value === question.value?.correct)
/** Fraction of the run completed, for the progress bar (0–100). */
const progress = computed(() =>
  store.questions.length
    ? ((store.currentIndex + 1) / store.questions.length) * 100
    : 0,
)

/**
 * The styling state of the option at shuffled display position `displayIndex`,
 * computed entirely in display space. `null` until the question is answered.
 *
 * @param displayIndex - Position of the option in the shuffled list.
 */
function optionState(displayIndex: number): 'correct' | 'incorrect' | 'neutral' | null {
  if (!answered.value || !shuffled.value) return null
  if (displayIndex === shuffled.value.correct) return 'correct'
  if (shuffled.value.order[displayIndex] === answer.value) return 'incorrect'
  return 'neutral'
}

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
  <section v-if="question && shuffled" class="card" aria-label="Quiz question">
    <div class="quiz-top">
      <span class="progress-text">
        Question <b>{{ store.currentIndex + 1 }}</b> of
        <b>{{ store.questions.length }}</b>
      </span>
      <div class="quiz-top__right">
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <button
          class="quiz-quit"
          type="button"
          aria-label="Quit quiz and return to topics"
          @click="store.reset()"
        >
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            />
          </svg>
          Quit
        </button>
      </div>
    </div>

    <h2 class="question">{{ question.question }}</h2>

    <div class="options">
      <button
        v-for="(option, i) in shuffled.options"
        :key="i"
        class="option"
        :class="optionState(i)"
        :disabled="answered"
        @click="choose(i)"
      >
        <span class="marker" aria-hidden="true">
          <svg
            v-if="optionState(i) === 'correct'"
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
          >
            <path
              d="M3 8.5l3.2 3.2L13 4.5"
              stroke="currentColor"
              stroke-width="2.4"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <svg
            v-else-if="optionState(i) === 'incorrect'"
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
          >
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
            />
          </svg>
          <template v-else>{{ String.fromCharCode(65 + i) }}</template>
        </span>
        <span class="label">{{ option }}</span>
        <span v-if="optionState(i) === 'correct'" class="tag">Correct</span>
        <span v-else-if="optionState(i) === 'incorrect'" class="tag">
          Your answer
        </span>
      </button>
    </div>

    <div
      v-if="answered"
      class="reveal"
      :class="isCorrect ? 'is-correct' : 'is-incorrect'"
      role="status"
    >
      <div class="reveal-head">
        <svg
          v-if="isCorrect"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.6" />
          <path
            d="M5 8.2l2 2 4-4.4"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <svg
          v-else
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.6" />
          <path
            d="M5.2 5.2l5.6 5.6M10.8 5.2l-5.6 5.6"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
          />
        </svg>
        {{ isCorrect ? 'Correct' : 'Incorrect' }}
      </div>
      <p v-if="question.explanation">{{ question.explanation }}</p>
    </div>

    <div v-if="answered" class="quiz-foot">
      <button class="btn btn-primary" @click="store.next()">
        {{ isLast ? 'See results' : 'Next' }}
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="M3 8h9M8.5 4l4 4-4 4"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>
  </section>
</template>
