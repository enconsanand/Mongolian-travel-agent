<script setup lang="ts">
const { lightLabel, darkLabel } = defineProps<{
  lightLabel: string
  darkLabel: string
}>()

const { theme, toggle } = useTheme()
const isDark = computed(() => theme.value === 'dark')
</script>

<template>
  <button
    type="button"
    class="grid h-9 w-9 place-items-center rounded-control border border-line text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
    :aria-label="isDark ? lightLabel : darkLabel"
    :title="isDark ? lightLabel : darkLabel"
    @click="toggle"
  >
    <ClientOnly>
      <i :class="isDark ? 'pi pi-sun' : 'pi pi-moon'" aria-hidden="true" />
      <template #fallback><i class="pi pi-moon opacity-0" aria-hidden="true" /></template>
    </ClientOnly>
  </button>
</template>
