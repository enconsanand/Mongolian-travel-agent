<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
<script lang="ts" setup>
const { chosen } = useTheme()

useHead(() => ({ htmlAttrs: { 'data-theme': chosen.value ?? undefined } }))
</script>
