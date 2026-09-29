<script lang="ts" setup>
defineProps({
  sidebarCollapsed: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-sidebar'])

const profileMenuOpen = ref(false)
const { userEmail } = useCookieAuth()
const { logout: authLogout } = useAuth()

const toggleProfileMenu = () => {
  profileMenuOpen.value = !profileMenuOpen.value
}

const logout = async () => {
  await authLogout()
}

const displayEmail = computed(() => userEmail.value || 'user@example.com')
const userInitials = computed(() => {
  if (userEmail.value) {
    const email = userEmail.value
    const namePart = email.split('@')[0] || 'UN'
    return namePart.substring(0, 2).toUpperCase()
  }
  return 'AT'
})

onMounted(() => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.profile-dropdown') && !target.closest('.profile-button')) profileMenuOpen.value = false
  })
})
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-200">
    <div class="flex items-center justify-between px-4 lg:px-6 py-4">
      <div class="flex items-center gap-4">
        <Button
          icon="pi pi-bars"
          severity="secondary"
          text
          class="hover:bg-slate-100 transition-colors duration-200"
          @click="emit('toggle-sidebar')"
        />
      </div>

      <div class="flex items-center gap-3">
        <div class="relative">
          <button
            class="profile-button flex items-center gap-2 p-2 rounded-lg hover:bg-slate-100 transition-colors"
            @click="toggleProfileMenu"
          >
            <div
              class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold"
            >
              {{ userInitials }}
            </div>
            <div class="hidden lg:block text-left">
              <p class="text-sm font-medium text-slate-900">{{ displayEmail.split('@')[0] }}</p>
            </div>
            <i class="pi pi-chevron-down text-xs text-slate-400" />
          </button>

          <div
            v-if="profileMenuOpen"
            class="profile-dropdown absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-slate-200 z-50"
          >
            <div class="px-4 py-3 border-b border-slate-200">
              <p class="font-medium text-slate-900">{{ displayEmail.split('@')[0] }}</p>
              <p class="text-sm text-slate-600">{{ displayEmail }}</p>
            </div>
            <div class="py-2">
              <button
                class="flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-slate-100 w-full text-left"
                @click="logout"
              >
                <i class="pi pi-sign-out" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
