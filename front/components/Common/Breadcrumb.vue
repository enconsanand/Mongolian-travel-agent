<script setup lang="ts">
interface BreadcrumbItem {
  label: string
  icon?: string
  href?: string
  active?: boolean
}

const { items } = defineProps<{
  items: BreadcrumbItem[]
}>()
</script>

<template>
  <nav class="flex items-center gap-2 text-sm text-slate-600">
    <template v-for="(item, index) in items" :key="index">
      <div class="flex items-center gap-2">
        <i v-if="item.icon" :class="item.icon" />
        <span v-if="item.active || !item.href" class="text-slate-900 font-medium">
          {{ item.label }}
        </span>
        <a v-else :href="item.href" class="hover:text-slate-900 transition-colors">
          {{ item.label }}
        </a>
      </div>
      <span v-if="index < items.length - 1" class="text-slate-400">/</span>
    </template>
  </nav>
</template>
