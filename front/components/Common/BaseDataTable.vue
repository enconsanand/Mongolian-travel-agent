<script setup lang="ts"></script>

<template>
  <div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
    <DataTable v-bind="$attrs" sort-mode="single" paginator :rows="10" striped-rows class="text-sm">
      <slot />
      <template #empty>
        <slot name="empty" />
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
:deep(.p-datatable .p-datatable-thead > tr > th) {
  background-color: #f9fafb;
  color: #374151;
  font-weight: 600;
}

:deep(.p-datatable .p-datatable-tbody > tr:hover) {
  background-color: #f3f4f6;
  transition: background-color 0.2s;
}
</style>
