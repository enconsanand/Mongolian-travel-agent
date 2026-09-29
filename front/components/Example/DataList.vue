<script lang="ts" setup>
import CommonBaseDataTable from '~/components/Common/BaseDataTable.vue'

interface User {
  id: number
  name: string
  email: string
  role: 'admin' | 'editor' | 'user'
  status: 'active' | 'inactive' | 'pending'
  department: string
  createdAt: string
}

interface Props {
  users: User[]
  isLoading: boolean
  formatDate: (date: string) => string
  getRoleColor: (role: string) => string
  getStatusColor: (status: string) => string
}

defineProps<Props>()

defineEmits<{
  'row-click': [user: User]
}>()
</script>

<template>
  <CommonBaseDataTable
    :value="users"
    :loading="isLoading"
    table-style="min-width: 60rem"
    @row-click="(event: any) => $emit('row-click', event.data)"
  >
    <template #empty>
      <div class="text-center py-8">
        <i class="pi pi-users text-4xl text-slate-300 mb-3" />
        <p class="text-slate-500">No users found matching your criteria</p>
      </div>
    </template>

    <Column field="id" header="ID" sortable style="width: 5rem">
      <template #body="{ data }">
        <span class="text-sm font-mono text-slate-600">#{{ data.id }}</span>
      </template>
    </Column>

    <Column field="name" header="Name" sortable style="min-width: 12rem">
      <template #body="{ data }">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
            {{ data.name.charAt(0) }}
          </div>
          <div>
            <span
              class="text-sm font-semibold text-gray-900 hover:text-blue-600 cursor-pointer"
              @click="$emit('row-click', data)"
            >
              {{ data.name }}
            </span>
          </div>
        </div>
      </template>
    </Column>

    <Column field="email" header="Email" sortable style="min-width: 14rem">
      <template #body="{ data }">
        <span class="text-sm text-slate-600 font-mono">{{ data.email }}</span>
      </template>
    </Column>

    <Column field="role" header="Role" sortable style="width: 8rem">
      <template #body="{ data }">
        <span class="px-2 py-1 rounded-md text-xs font-medium capitalize border" :class="getRoleColor(data.role)">
          {{ data.role }}
        </span>
      </template>
    </Column>

    <Column field="status" header="Status" sortable style="width: 8rem">
      <template #body="{ data }">
        <span class="px-2 py-1 rounded-md text-xs font-medium capitalize border" :class="getStatusColor(data.status)">
          {{ data.status }}
        </span>
      </template>
    </Column>

    <Column field="department" header="Department" sortable style="min-width: 10rem">
      <template #body="{ data }">
        <span class="text-sm text-slate-700">{{ data.department }}</span>
      </template>
    </Column>

    <Column field="createdAt" header="Created" sortable style="width: 10rem">
      <template #body="{ data }">
        <span class="text-sm text-slate-500">{{ formatDate(data.createdAt) }}</span>
      </template>
    </Column>

    <Column header="Actions" style="width: 6rem">
      <template #body="{ data }">
        <div class="flex gap-1">
          <Button
            v-tooltip.top="'View Details'"
            icon="pi pi-eye"
            size="small"
            text
            rounded
            severity="secondary"
            @click="$emit('row-click', data)"
          />
          <Button v-tooltip.top="'Edit'" icon="pi pi-pencil" size="small" text rounded severity="secondary" />
        </div>
      </template>
    </Column>
  </CommonBaseDataTable>
</template>
