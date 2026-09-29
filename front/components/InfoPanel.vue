<template>
  <div class="info-panel">
    <div class="text-center p-8">
      <i class="pi pi-exclamation-triangle text-6xl text-yellow-500 mb-4" :aria-label="altText" />
      <h2 class="text-2xl font-semibold mb-2">{{ title }}</h2>
      <p class="text-gray-600">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  message: string
  altText?: string
}

withDefaults(defineProps<Props>(), {
  altText: 'Information',
})
</script>

<style scoped>
.info-panel {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
