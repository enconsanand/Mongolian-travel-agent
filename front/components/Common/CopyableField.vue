<script lang="ts" setup>
interface Props {
  label: string
  value?: string
  mono?: boolean
  breakAll?: boolean
  multiline?: boolean
}

defineProps<Props>()

defineEmits<{
  copy: [text: string]
}>()
</script>

<template>
  <div class="space-y-1">
    <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide">{{ label }}</label>
    <div v-if="value" class="flex items-start gap-2">
      <div class="flex-1 min-w-0">
        <div
          class="text-sm bg-gray-50 px-3 py-1 rounded-md"
          :class="[
            mono ? 'font-mono' : 'font-semibold',
            breakAll ? 'break-all' : '',
            multiline ? 'leading-relaxed' : '',
            'text-gray-900',
          ]"
        >
          {{ value }}
        </div>
      </div>
      <Button
        v-tooltip="'Copy'"
        icon="pi pi-copy"
        size="small"
        severity="secondary"
        text
        class="shrink-0 opacity-50 hover:opacity-100 transition-opacity"
        @click="$emit('copy', value)"
      />
    </div>
    <div v-else class="text-sm font-mono bg-gray-50 px-3 py-1 rounded-md">-</div>
  </div>
</template>
