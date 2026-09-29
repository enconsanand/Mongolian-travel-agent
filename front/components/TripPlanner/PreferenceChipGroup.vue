<script setup lang="ts">
import PreferenceCardFrame from '~/components/TripPlanner/PreferenceCardFrame.vue'
import type { ChipPreferenceCard } from '~/types/trip-planner'

const { card, requiredLabel, customValueLabel } = defineProps<{
  card: ChipPreferenceCard
  requiredLabel: string
  customValueLabel: string
}>()

const emit = defineEmits<{
  'select-preset': [optionId: string]
  'set-custom': [rawValue: string]
}>()

const isCustomSelected = computed(() => card.selection?.kind === 'custom')

const customAmount = computed(() => (card.selection?.kind === 'custom' ? String(card.selection.amount) : ''))

function isPresetSelected(optionId: string): boolean {
  return card.selection?.kind === 'preset' && card.selection.optionId === optionId
}

function onCustomInput(event: Event) {
  const input = event.target as HTMLInputElement
  emit('set-custom', input.value)
}
</script>

<template>
  <PreferenceCardFrame
    :title="card.title"
    :icon="card.icon"
    :required-label="requiredLabel"
    :show-missing="card.showMissing"
  >
    <div class="flex flex-wrap gap-3" role="group" :aria-label="card.title" aria-required="true">
      <button
        v-for="option in card.options"
        :key="option.id"
        type="button"
        class="choice-chip"
        :aria-pressed="isPresetSelected(option.id)"
        @click="emit('select-preset', option.id)"
      >
        {{ option.label }}
      </button>
      <label v-if="card.customField" class="custom-choice" :data-active="isCustomSelected">
        <span>{{ customValueLabel }}</span>
        <input
          class="planner-field"
          type="number"
          inputmode="numeric"
          min="1"
          :placeholder="card.customField.placeholder"
          :aria-label="card.customField.ariaLabel"
          :value="customAmount"
          @input="onCustomInput"
        />
        <span class="pr-2">{{ card.customField.unit }}</span>
      </label>
    </div>
  </PreferenceCardFrame>
</template>
