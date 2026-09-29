<script setup lang="ts">
defineProps<{
  title: string
  icon: string
  requiredLabel: string
  showMissing: boolean
}>()
</script>

<template>
  <div class="glass-panel rounded-2xl p-5" :data-missing="showMissing">
    <h2 class="mb-4 flex items-center gap-2 text-base font-semibold">
      <i :class="icon" class="text-lg text-cyan-400" aria-hidden="true" />
      {{ title }}
      <span class="text-xs font-medium text-rose-300">{{ requiredLabel }}</span>
    </h2>
    <slot />
  </div>
</template>
