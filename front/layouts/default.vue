<script lang="ts" setup>
import Sidebar from '~/components/Common/Sidebar.vue'
import TopHeader from '~/components/Common/TopHeader.vue'
import { ref, onMounted, onUnmounted } from 'vue'

const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false)
const windowWidth = ref(0)

const toggleSidebar = () => {
  if (windowWidth.value < 1024) {
    sidebarOpen.value = !sidebarOpen.value
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

const updateWindowWidth = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  updateWindowWidth()
  window.addEventListener('resize', updateWindowWidth)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateWindowWidth)
})

const closeSidebar = () => {
  sidebarOpen.value = false
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <div v-if="sidebarOpen" class="fixed inset-0 z-40 bg-black/50 lg:hidden" @click="closeSidebar" />

    <TopHeader :sidebar-collapsed="sidebarCollapsed" @toggle-sidebar="toggleSidebar" />

    <Sidebar :open="sidebarOpen" :collapsed="sidebarCollapsed" @close="closeSidebar" />

    <div class="transition-all duration-300 pt-[73px]" :class="sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'">
      <main class="min-h-[calc(100vh-73px)]">
        <slot />
      </main>
    </div>
  </div>
</template>
