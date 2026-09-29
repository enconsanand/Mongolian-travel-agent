<script setup lang="ts">
interface Props {
  rows?: number
  columns?: number
}

withDefaults(defineProps<Props>(), {
  rows: 10,
  columns: 6,
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
    <div>
      <div class="bg-slate-50 p-4 border-b border-slate-200">
        <div class="grid gap-4" :style="`grid-template-columns: repeat(${columns}, 1fr)`">
          <div v-for="col in columns" :key="col" class="h-4 bg-slate-200 rounded animate-pulse" />
        </div>
      </div>

      <div class="divide-y divide-slate-200">
        <div v-for="row in rows" :key="row" class="p-4">
          <div class="grid gap-4" :style="`grid-template-columns: repeat(${columns}, 1fr)`">
            <div
              v-for="col in columns"
              :key="col"
              class="h-4 bg-slate-200 rounded animate-pulse"
              :class="{ 'w-3/4': col === 1, 'w-1/2': col > 3 }"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
