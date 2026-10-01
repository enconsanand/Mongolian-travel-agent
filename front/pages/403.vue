<script setup lang="ts">
definePageMeta({ layout: 'planner' })
</script>

<template>
  <section class="mx-auto max-w-md px-6 py-24 text-center">
    <i class="pi pi-lock text-4xl text-ink-subtle" aria-hidden="true" />
    <h1 class="mt-4 text-2xl font-bold">403 - Forbidden</h1>
    <p class="mt-2 text-ink-muted">You do not have permission to access this page.</p>
    <NuxtLink to="/" class="mt-6 inline-block text-brand underline">Home</NuxtLink>
  </section>
</template>
