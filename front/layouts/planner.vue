<script setup lang="ts">
useHead({
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&display=swap',
    },
  ],
})
</script>

<template>
  <div class="trip-planner relative z-0 min-h-screen antialiased">
    <slot />
  </div>
</template>
