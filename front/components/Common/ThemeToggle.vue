<script setup lang="ts">
const { lightLabel, darkLabel } = defineProps<{
  lightLabel: string
  darkLabel: string
}>()

const { chosen, theme, toggle } = useTheme()
// The server only knows the cookie, not the system preference: render from the cookie until mounted so the
// label hydrates without a mismatch, then follow the real theme
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})
const isDark = computed(() => (mounted.value ? theme.value : chosen.value) === 'dark')
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
