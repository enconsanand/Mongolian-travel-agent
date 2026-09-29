<script lang="ts" setup>
import CommonBreadcrumb from '~/components/Common/Breadcrumb.vue'
import CommonDraggableModal from '~/components/Common/DraggableModal.vue'
import ExampleFilters from '~/components/Example/Filters.vue'
import ExampleDataList from '~/components/Example/DataList.vue'
import CommonCopyableField from '~/components/Common/CopyableField.vue'
import CommonSkeletonTable from '~/components/Common/SkeletonTable.vue'

definePageMeta({
  title: 'Example - DataTable with Filters',
  layout: 'default',
})

interface User {
  id: number
  name: string
  email: string
  role: 'admin' | 'editor' | 'user'
  status: 'active' | 'inactive' | 'pending'
  department: string
  createdAt: string
}

const { $toast } = useNuxtApp()

// Mock data
const mockUsers: User[] = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com',
    role: 'admin',
    status: 'active',
    department: 'Engineering',
    createdAt: '2024-01-15',
  },
  {
    id: 2,
    name: 'Jane Smith',
    email: 'jane@example.com',
    role: 'editor',
    status: 'active',
    department: 'Marketing',
    createdAt: '2024-02-20',
  },
  {
    id: 3,
    name: 'Bob Wilson',
    email: 'bob@example.com',
    role: 'user',
    status: 'inactive',
    department: 'Sales',
    createdAt: '2024-03-10',
  },
  {
    id: 4,
    name: 'Alice Brown',
    email: 'alice@example.com',
    role: 'editor',
    status: 'active',
    department: 'Design',
    createdAt: '2024-04-05',
  },
  {
    id: 5,
    name: 'Charlie Davis',
    email: 'charlie@example.com',
    role: 'user',
    status: 'pending',
    department: 'Engineering',
    createdAt: '2024-05-12',
  },
  {
    id: 6,
    name: 'Diana Miller',
    email: 'diana@example.com',
    role: 'admin',
    status: 'active',
    department: 'HR',
    createdAt: '2024-06-18',
  },
  {
    id: 7,
    name: 'Edward Jones',
    email: 'edward@example.com',
    role: 'user',
    status: 'active',
    department: 'Finance',
    createdAt: '2024-07-22',
  },
  {
    id: 8,
    name: 'Fiona Garcia',
    email: 'fiona@example.com',
    role: 'editor',
    status: 'inactive',
    department: 'Marketing',
    createdAt: '2024-08-30',
  },
  {
    id: 9,
    name: 'George Martinez',
    email: 'george@example.com',
    role: 'user',
    status: 'pending',
    department: 'Engineering',
    createdAt: '2024-09-14',
  },
  {
    id: 10,
    name: 'Hannah Lee',
    email: 'hannah@example.com',
    role: 'admin',
    status: 'active',
    department: 'Operations',
    createdAt: '2024-10-25',
  },
]

const users = ref<User[]>([])
const isLoading = ref(true)
const isRefreshing = ref(false)

// Filter states
const searchQuery = ref('')
const selectedRole = ref('all')
const selectedStatus = ref('all')
const selectedDepartment = ref('all')

// Modal states
const detailModalVisible = ref(false)
const selectedUser = ref<User | null>(null)

const breadcrumbItems = [
  { label: 'Home', icon: 'pi pi-home', href: '/' },
  { label: 'Example', active: true },
]

// Computed filtered users
const filteredUsers = computed(() => {
  return users.value.filter((user) => {
    const matchesSearch =
      !searchQuery.value ||
      user.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      user.department.toLowerCase().includes(searchQuery.value.toLowerCase())

    const matchesRole = selectedRole.value === 'all' || user.role === selectedRole.value
    const matchesStatus = selectedStatus.value === 'all' || user.status === selectedStatus.value
    const matchesDepartment = selectedDepartment.value === 'all' || user.department === selectedDepartment.value

    return matchesSearch && matchesRole && matchesStatus && matchesDepartment
  })
})

// Unique departments for filter
const departments = computed(() => {
  const depts = [...new Set(mockUsers.map((u) => u.department))]
  return ['all', ...depts]
})

// Simulate loading data
const loadUsers = async () => {
  isLoading.value = true
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 800))
  users.value = [...mockUsers]
  isLoading.value = false
}

const handleRefresh = async () => {
  isRefreshing.value = true
  $toast.info('Refreshing data...')
  await new Promise((resolve) => setTimeout(resolve, 500))
  users.value = [...mockUsers]
  isRefreshing.value = false
  $toast.success('Data refreshed!')
}

const handleRowClick = (user: User) => {
  selectedUser.value = user
  detailModalVisible.value = true
}

const handleCopy = (text: string) => {
  navigator.clipboard.writeText(text)
  $toast.success('Copied to clipboard!')
}

const getRoleColor = (role: string) => {
  switch (role) {
    case 'admin':
      return 'bg-purple-100 text-purple-700 border-purple-200'
    case 'editor':
      return 'bg-blue-100 text-blue-700 border-blue-200'
    case 'user':
      return 'bg-slate-100 text-slate-700 border-slate-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-700 border-green-200'
    case 'inactive':
      return 'bg-red-100 text-red-700 border-red-200'
    case 'pending':
      return 'bg-yellow-100 text-yellow-700 border-yellow-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Header Section -->
    <div class="bg-white border-b border-slate-200">
      <div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex flex-col gap-6">
          <div class="flex items-center justify-between">
            <CommonBreadcrumb :items="breadcrumbItems" />
            <Button
              icon="pi pi-refresh"
              severity="secondary"
              outlined
              label="Refresh"
              size="small"
              :loading="isRefreshing"
              @click="handleRefresh"
            />
          </div>

          <!-- Filters -->
          <div class="bg-slate-50 rounded-lg border border-slate-200">
            <ExampleFilters
              v-model:search-query="searchQuery"
              v-model:selected-role="selectedRole"
              v-model:selected-status="selectedStatus"
              v-model:selected-department="selectedDepartment"
              :departments="departments"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Content Section -->
    <div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading State -->
      <div v-if="isLoading" class="space-y-6">
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div class="flex items-center justify-between">
            <div class="space-y-2">
              <div class="h-6 w-32 bg-slate-200 rounded animate-pulse" />
              <div class="h-4 w-48 bg-slate-200 rounded animate-pulse" />
            </div>
            <div class="text-center">
              <div class="h-8 w-16 bg-slate-200 rounded animate-pulse mb-2" />
              <div class="h-3 w-12 bg-slate-200 rounded animate-pulse" />
            </div>
          </div>
        </div>
        <CommonSkeletonTable :rows="8" :columns="6" />
      </div>

      <!-- Content State -->
      <div v-else class="space-y-6">
        <!-- Summary Card -->
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold text-slate-900 mb-2 flex items-center gap-2">
                <i class="pi pi-users text-blue-500" />
                User Management
              </h2>
              <p class="text-sm text-slate-600">Showing {{ filteredUsers.length }} of {{ users.length }} users</p>
            </div>
            <div class="flex items-center gap-6">
              <div class="text-center">
                <div class="text-2xl font-bold text-blue-600">{{ filteredUsers.length }}</div>
                <div class="text-xs text-slate-500 uppercase tracking-wide font-medium">Filtered</div>
              </div>
              <div class="w-px h-12 bg-slate-200" />
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-600">{{ users.length }}</div>
                <div class="text-xs text-slate-500 uppercase tracking-wide font-medium">Total</div>
              </div>
            </div>
          </div>
        </div>

        <!-- DataTable -->
        <ExampleDataList
          :users="filteredUsers"
          :is-loading="isRefreshing"
          :format-date="formatDate"
          :get-role-color="getRoleColor"
          :get-status-color="getStatusColor"
          @row-click="handleRowClick"
        />
      </div>
    </div>

    <!-- Detail Modal -->
    <CommonDraggableModal
      v-model:visible="detailModalVisible"
      :title="selectedUser ? `User Details: ${selectedUser.name}` : 'Loading...'"
      :hide-confirm="true"
      cancel-text="Close"
      width="600px"
    >
      <div v-if="selectedUser" class="space-y-6">
        <!-- Status Banner -->
        <!-- prettier-ignore -->
        <div
          class="rounded-xl p-4 flex items-center justify-between"
          :class="
            selectedUser.status === 'active'
              ? 'bg-green-50 border border-green-200'
              : selectedUser.status === 'pending'
                ? 'bg-yellow-50 border border-yellow-200'
                : 'bg-red-50 border border-red-200'
          "
        >
          <div class="flex items-center gap-3">
            <div
              class="w-12 h-12 rounded-full flex items-center justify-center text-white text-lg font-bold"
              :class="
                selectedUser.status === 'active'
                  ? 'bg-green-500'
                  : selectedUser.status === 'pending'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
              "
            >
              {{ selectedUser.name.charAt(0) }}
            </div>
            <div>
              <h3 class="font-semibold text-slate-900">{{ selectedUser.name }}</h3>
              <p class="text-sm text-slate-600">{{ selectedUser.email }}</p>
            </div>
          </div>
          <span
            class="px-3 py-1 rounded-full text-sm font-medium capitalize"
            :class="getStatusColor(selectedUser.status)"
          >
            {{ selectedUser.status }}
          </span>
        </div>

        <!-- Details Grid -->
        <div class="grid grid-cols-2 gap-4">
          <CommonCopyableField label="User ID" :value="String(selectedUser.id)" mono @copy="handleCopy" />
          <CommonCopyableField label="Email" :value="selectedUser.email" mono @copy="handleCopy" />
          <div class="space-y-1">
            <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide">Role</label>
            <span
              class="inline-block px-3 py-1 rounded-md text-sm font-medium capitalize border"
              :class="getRoleColor(selectedUser.role)"
            >
              {{ selectedUser.role }}
            </span>
          </div>
          <div class="space-y-1">
            <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide">Department</label>
            <span class="text-sm font-medium text-slate-900">{{ selectedUser.department }}</span>
          </div>
          <div class="space-y-1 col-span-2">
            <label class="block text-xs font-medium text-slate-500 uppercase tracking-wide">Created At</label>
            <span class="text-sm text-slate-700">{{ formatDate(selectedUser.createdAt) }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-4 border-t border-slate-200">
          <Button label="Edit User" icon="pi pi-pencil" size="small" outlined />
          <Button label="Send Email" icon="pi pi-envelope" size="small" outlined severity="secondary" />
          <Button
            v-if="selectedUser.status !== 'active'"
            label="Activate"
            icon="pi pi-check"
            size="small"
            severity="success"
          />
          <Button v-else label="Deactivate" icon="pi pi-times" size="small" severity="danger" outlined />
        </div>
      </div>
    </CommonDraggableModal>
  </div>
</template>
