<script setup lang="ts">
import CommonBreadcrumb from '~/components/Common/Breadcrumb.vue'
import CommonEmptyState from '~/components/Common/EmptyState.vue'
import CommonCopyableField from '~/components/Common/CopyableField.vue'
import CommonSkeletonCard from '~/components/Common/SkeletonCard.vue'
import CommonSkeletonTable from '~/components/Common/SkeletonTable.vue'
import CommonDraggableModal from '~/components/Common/DraggableModal.vue'
import CommonBaseDataTable from '~/components/Common/BaseDataTable.vue'

definePageMeta({
  title: 'Components',
  layout: 'default',
})

const toast = useNuxtApp().$toast

// Breadcrumb demo data
const breadcrumbItems = [
  { label: 'Home', icon: 'pi pi-home', href: '/' },
  { label: 'Components', href: '/components' },
  { label: 'Breadcrumb', active: true },
]

// DataTable demo data
const tableData = ref([
  { id: 1, name: 'John Doe', email: 'john@example.com', role: 'Admin' },
  { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'User' },
  { id: 3, name: 'Bob Wilson', email: 'bob@example.com', role: 'Editor' },
])

// Modal state
const modalVisible = ref(false)

// Copy handler
const handleCopy = (text: string) => {
  navigator.clipboard.writeText(text)
  toast.success('Copied to clipboard')
}

// Modal confirm handler
const handleModalConfirm = () => {
  modalVisible.value = false
  toast.success('Confirmed!')
}
</script>

<template>
  <div class="space-y-8 p-6">
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Component Showcase</h1>
        <p class="text-slate-600 mt-1">All available UI components in this template</p>
      </div>
    </div>

    <!-- Breadcrumb -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Breadcrumb</h2>
      <p class="text-sm text-slate-600 mb-4">Navigation breadcrumb with icons and links.</p>
      <div class="p-4 bg-slate-50 rounded-lg">
        <CommonBreadcrumb :items="breadcrumbItems" />
      </div>
      <div class="mt-4 p-4 bg-slate-900 rounded-lg overflow-x-auto">
        <pre class="text-sm text-green-400"><code>&lt;CommonBreadcrumb :items="[
  { label: 'Home', icon: 'pi pi-home', href: '/' },
  { label: 'Components', href: '/components' },
  { label: 'Current', active: true },
]" /&gt;</code></pre>
      </div>
    </section>

    <!-- Buttons (PrimeVue) -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Buttons (PrimeVue)</h2>
      <p class="text-sm text-slate-600 mb-4">Various button styles from PrimeVue.</p>
      <div class="p-4 bg-slate-50 rounded-lg space-y-4">
        <div class="flex flex-wrap gap-3">
          <Button label="Primary" />
          <Button label="Secondary" severity="secondary" />
          <Button label="Success" severity="success" />
          <Button label="Warning" severity="warn" />
          <Button label="Danger" severity="danger" />
          <Button label="Info" severity="info" />
        </div>
        <div class="flex flex-wrap gap-3">
          <Button label="Outlined" outlined />
          <Button label="Text" text />
          <Button label="With Icon" icon="pi pi-check" />
          <Button icon="pi pi-search" aria-label="Search" />
          <Button label="Loading" loading />
        </div>
        <div class="flex flex-wrap gap-3">
          <Button label="Small" size="small" />
          <Button label="Normal" />
          <Button label="Large" size="large" />
        </div>
      </div>
    </section>

    <!-- Form Inputs (PrimeVue) -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Form Inputs (PrimeVue)</h2>
      <p class="text-sm text-slate-600 mb-4">Form input components from PrimeVue.</p>
      <div class="p-4 bg-slate-50 rounded-lg grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">InputText</label>
          <InputText placeholder="Enter text..." class="w-full" />
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">Password</label>
          <Password placeholder="Enter password..." class="w-full" :feedback="false" toggle-mask />
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">Textarea</label>
          <Textarea placeholder="Enter description..." rows="3" class="w-full" />
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">Select</label>
          <Select
            :options="[
              { label: 'Option 1', value: 1 },
              { label: 'Option 2', value: 2 },
              { label: 'Option 3', value: 3 },
            ]"
            option-label="label"
            option-value="value"
            placeholder="Select an option"
            class="w-full"
          />
        </div>
      </div>
    </section>

    <!-- CopyableField -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">CopyableField</h2>
      <p class="text-sm text-slate-600 mb-4">Field with copy-to-clipboard functionality.</p>
      <div class="p-4 bg-slate-50 rounded-lg grid grid-cols-1 md:grid-cols-2 gap-4">
        <CommonCopyableField label="API Key" value="sk-1234567890abcdef" mono @copy="handleCopy" />
        <CommonCopyableField label="User ID" value="user_abc123" @copy="handleCopy" />
      </div>
      <div class="mt-4 p-4 bg-slate-900 rounded-lg overflow-x-auto">
        <pre class="text-sm text-green-400"><code>&lt;CommonCopyableField
  label="API Key"
  value="sk-1234567890abcdef"
  mono
  @copy="handleCopy"
/&gt;</code></pre>
      </div>
    </section>

    <!-- EmptyState -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">EmptyState</h2>
      <p class="text-sm text-slate-600 mb-4">Placeholder for empty content areas.</p>
      <div class="p-4 bg-slate-50 rounded-lg">
        <CommonEmptyState
          icon="pi pi-inbox"
          title="No data available"
          description="There are no items to display at the moment."
          :features="[
            { icon: 'pi pi-plus', label: 'Add new' },
            { icon: 'pi pi-refresh', label: 'Refresh' },
          ]"
        />
      </div>
      <div class="mt-4 p-4 bg-slate-900 rounded-lg overflow-x-auto">
        <pre class="text-sm text-green-400"><code>&lt;CommonEmptyState
  icon="pi pi-inbox"
  title="No data available"
  description="There are no items to display."
  :features="[
    { icon: 'pi pi-plus', label: 'Add new' },
    { icon: 'pi pi-refresh', label: 'Refresh' },
  ]"
/&gt;</code></pre>
      </div>
    </section>

    <!-- BaseDataTable -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">BaseDataTable</h2>
      <p class="text-sm text-slate-600 mb-4">Styled data table wrapper for PrimeVue DataTable.</p>
      <div class="p-4 bg-slate-50 rounded-lg">
        <CommonBaseDataTable :value="tableData">
          <Column field="id" header="ID" sortable />
          <Column field="name" header="Name" sortable />
          <Column field="email" header="Email" sortable />
          <Column field="role" header="Role" sortable />
        </CommonBaseDataTable>
      </div>
    </section>

    <!-- Skeleton Loaders -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Skeleton Loaders</h2>
      <p class="text-sm text-slate-600 mb-4">Loading placeholders for cards and tables.</p>
      <div class="space-y-6">
        <div>
          <h3 class="text-sm font-medium text-slate-700 mb-3">SkeletonCard</h3>
          <CommonSkeletonCard />
        </div>
        <div>
          <h3 class="text-sm font-medium text-slate-700 mb-3">SkeletonTable (rows: 3, columns: 4)</h3>
          <CommonSkeletonTable :rows="3" :columns="4" />
        </div>
      </div>
    </section>

    <!-- DraggableModal -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">DraggableModal</h2>
      <p class="text-sm text-slate-600 mb-4">Draggable modal dialog with customizable actions.</p>
      <div class="p-4 bg-slate-50 rounded-lg">
        <Button label="Open Modal" icon="pi pi-external-link" @click="modalVisible = true" />
      </div>
      <CommonDraggableModal
        v-model:visible="modalVisible"
        title="Example Modal"
        subtitle="This modal can be dragged around"
        confirm-text="Save"
        cancel-text="Cancel"
        @confirm="handleModalConfirm"
      >
        <div class="space-y-4">
          <p class="text-slate-600">This is a draggable modal. You can drag it by the header bar.</p>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700">Sample Input</label>
            <InputText placeholder="Enter something..." class="w-full" />
          </div>
        </div>
      </CommonDraggableModal>
      <div class="mt-4 p-4 bg-slate-900 rounded-lg overflow-x-auto">
        <pre class="text-sm text-green-400"><code>&lt;CommonDraggableModal
  v-model:visible="modalVisible"
  title="Modal Title"
  subtitle="Optional subtitle"
  confirm-text="Save"
  cancel-text="Cancel"
  @confirm="handleConfirm"
&gt;
  &lt;!-- Modal content --&gt;
&lt;/CommonDraggableModal&gt;</code></pre>
      </div>
    </section>

    <!-- Messages & Toasts -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Messages & Toasts</h2>
      <p class="text-sm text-slate-600 mb-4">Toast notifications and inline messages.</p>
      <div class="p-4 bg-slate-50 rounded-lg space-y-4">
        <div class="flex flex-wrap gap-3">
          <Button label="Success Toast" severity="success" @click="toast.success('Operation successful!')" />
          <Button label="Error Toast" severity="danger" @click="toast.error('Something went wrong!')" />
          <Button label="Info Toast" severity="info" @click="toast.info('Here is some information.')" />
          <Button label="Warning Toast" severity="warn" @click="toast.warn('Please be careful!')" />
        </div>
        <div class="space-y-2">
          <Message severity="success" :closable="false">Success message</Message>
          <Message severity="error" :closable="false">Error message</Message>
          <Message severity="info" :closable="false">Info message</Message>
          <Message severity="warn" :closable="false">Warning message</Message>
        </div>
      </div>
    </section>

    <!-- Progress & Loading -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Progress & Loading</h2>
      <p class="text-sm text-slate-600 mb-4">Progress indicators and loading states.</p>
      <div class="p-4 bg-slate-50 rounded-lg space-y-6">
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700">ProgressBar</label>
          <ProgressBar :value="65" />
        </div>
        <div class="flex items-center gap-6">
          <div class="text-center">
            <ProgressSpinner style="width: 50px; height: 50px" />
            <p class="text-sm text-slate-600 mt-2">Spinner</p>
          </div>
          <div class="text-center">
            <i class="pi pi-spin pi-spinner text-3xl text-blue-500" />
            <p class="text-sm text-slate-600 mt-2">Icon Spinner</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Tags & Badges -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Tags & Badges</h2>
      <p class="text-sm text-slate-600 mb-4">Labels, tags, and status indicators.</p>
      <div class="p-4 bg-slate-50 rounded-lg space-y-4">
        <div class="flex flex-wrap gap-3">
          <Tag value="Primary" />
          <Tag value="Success" severity="success" />
          <Tag value="Warning" severity="warn" />
          <Tag value="Danger" severity="danger" />
          <Tag value="Info" severity="info" />
          <Tag value="Secondary" severity="secondary" />
        </div>
        <div class="flex flex-wrap gap-3">
          <Tag value="With Icon" icon="pi pi-check" severity="success" />
          <Tag value="Rounded" rounded />
        </div>
      </div>
    </section>

    <!-- Icons -->
    <section class="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h2 class="text-lg font-semibold text-slate-900 mb-4">Icons (PrimeIcons)</h2>
      <p class="text-sm text-slate-600 mb-4">
        Common icons from PrimeIcons.
        <a href="https://primevue.org/icons/" target="_blank" class="text-blue-600 hover:underline">View all icons</a>
      </p>
      <div class="p-4 bg-slate-50 rounded-lg">
        <div class="grid grid-cols-6 md:grid-cols-10 gap-4">
          <div
            v-for="icon in [
              'pi-home',
              'pi-user',
              'pi-cog',
              'pi-search',
              'pi-check',
              'pi-times',
              'pi-plus',
              'pi-minus',
              'pi-pencil',
              'pi-trash',
              'pi-download',
              'pi-upload',
              'pi-refresh',
              'pi-sync',
              'pi-save',
              'pi-print',
              'pi-eye',
              'pi-eye-slash',
              'pi-lock',
              'pi-unlock',
            ]"
            :key="icon"
            class="text-center p-3 bg-white rounded-lg border border-slate-200 hover:border-blue-300 transition-colors"
          >
            <i :class="`pi ${icon}`" class="text-xl text-slate-700" />
            <p class="text-xs text-slate-500 mt-2 truncate">{{ icon }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
