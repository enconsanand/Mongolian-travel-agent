<script setup lang="ts">
definePageMeta({
  layout: 'default',
  middleware: 'guest',
})
</script>

<template>
  <div class="p-5">
    <div class="w-full">
      <Card class="bg-white rounded-lg shadow-none">
        <template #content>
          <InfoPanel
            alt-text="Forbidden"
            title="403 - Forbidden"
            message="You do not have permission to access this page."
          />
        </template>
      </Card>
    </div>
  </div>
</template>
