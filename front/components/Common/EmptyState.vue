<script setup lang="ts">
interface Feature {
  icon: string
  label: string
}

interface EmptyStateProps {
  icon?: string
  title: string
  description: string
  features?: Feature[]
  maxWidth?: string
}

const {
  icon = 'pi pi-chart-bar',
  title,
  description,
  features = [],
  maxWidth = 'max-w-md',
} = defineProps<EmptyStateProps>()
</script>

<template>
  <div class="text-center py-16">
    <div class="bg-white rounded-xl p-12 shadow-sm border border-slate-200 mx-auto" :class="maxWidth">
      <div
        class="bg-linear-to-br from-blue-50 to-sky-50 rounded-full w-24 h-24 flex items-center justify-center mx-auto mb-6"
      >
        <i :class="icon" class="text-4xl text-blue-500" />
      </div>

      <h3 class="text-xl font-semibold text-slate-900 mb-3">
        {{ title }}
      </h3>

      <p class="text-slate-600 mb-6 leading-relaxed">
        {{ description }}
      </p>

      <div v-if="features.length > 0" class="flex items-center justify-center gap-4 text-sm text-slate-500">
        <div v-for="feature in features" :key="feature.label" class="flex items-center gap-2">
          <i :class="feature.icon" />
          <span>{{ feature.label }}</span>
        </div>
      </div>

      <slot />
    </div>
  </div>
</template>
