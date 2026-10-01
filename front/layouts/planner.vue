<script setup lang="ts">
import { BRAND } from '~/constants/brand'

const year = new Date().getFullYear()
</script>

<template>
  <div class="trip-planner relative z-0 flex min-h-screen flex-col antialiased">
    <div class="flex-1">
      <slot />
    </div>
    <footer class="border-t border-line py-6 text-center text-xs text-ink-subtle">© {{ year }} {{ BRAND.name }}</footer>
  </div>
</template>
