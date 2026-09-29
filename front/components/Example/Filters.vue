<script setup lang="ts">
interface Props {
  searchQuery: string
  selectedRole?: string
  selectedStatus?: string
  selectedDepartment?: string
  departments?: string[]
  placeholder?: string
}

interface Emits {
  (e: 'update:searchQuery', value: string): void
  (e: 'update:selectedRole', value: string): void
  (e: 'update:selectedStatus', value: string): void
  (e: 'update:selectedDepartment', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  selectedRole: 'all',
  selectedStatus: 'all',
  selectedDepartment: 'all',
  departments: () => ['all'],
  placeholder: 'Search by name, email, or department...',
})

const emit = defineEmits<Emits>()

const roleOptions = [
  { label: 'All Roles', value: 'all' },
  { label: 'Admin', value: 'admin' },
  { label: 'Editor', value: 'editor' },
  { label: 'User', value: 'user' },
]

const statusOptions = [
  { label: 'All Status', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
  { label: 'Pending', value: 'pending' },
]

const departmentOptions = computed(() =>
  props.departments.map((dept) => ({
    label: dept === 'all' ? 'All Departments' : dept,
    value: dept,
  }))
)

const localSearchQuery = computed({
  get: () => props.searchQuery,
  set: (value) => emit('update:searchQuery', value),
})

const localSelectedRole = computed({
  get: () => props.selectedRole,
  set: (value) => emit('update:selectedRole', value || 'all'),
})

const localSelectedStatus = computed({
  get: () => props.selectedStatus,
  set: (value) => emit('update:selectedStatus', value || 'all'),
})

const localSelectedDepartment = computed({
  get: () => props.selectedDepartment,
  set: (value) => emit('update:selectedDepartment', value || 'all'),
})

const hasActiveFilters = computed(() => {
  return (
    props.searchQuery ||
    props.selectedRole !== 'all' ||
    props.selectedStatus !== 'all' ||
    props.selectedDepartment !== 'all'
  )
})

const clearFilters = () => {
  emit('update:searchQuery', '')
  emit('update:selectedRole', 'all')
  emit('update:selectedStatus', 'all')
  emit('update:selectedDepartment', 'all')
}
</script>

<template>
  <div class="p-4">
    <div class="flex flex-wrap items-center gap-4">
      <!-- Search Input -->
      <div class="flex-1 min-w-64">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText v-model="localSearchQuery" :placeholder="placeholder" class="w-full pl-10" size="small" />
        </IconField>
      </div>

      <!-- Role Filter -->
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-slate-700">Role:</span>
        <Select
          v-model="localSelectedRole"
          :options="roleOptions"
          option-label="label"
          option-value="value"
          class="w-32"
          size="small"
        />
      </div>

      <!-- Status Filter -->
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-slate-700">Status:</span>
        <Select
          v-model="localSelectedStatus"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          class="w-32"
          size="small"
        />
      </div>

      <!-- Department Filter -->
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-slate-700">Dept:</span>
        <Select
          v-model="localSelectedDepartment"
          :options="departmentOptions"
          option-label="label"
          option-value="value"
          class="w-40"
          size="small"
        />
      </div>

      <!-- Clear Filters Button -->
      <Button
        v-if="hasActiveFilters"
        icon="pi pi-filter-slash"
        label="Clear"
        severity="secondary"
        text
        size="small"
        @click="clearFilters"
      />
    </div>
  </div>
</template>
