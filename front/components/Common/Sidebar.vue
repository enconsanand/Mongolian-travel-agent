<script lang="ts" setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const route = useRoute()

interface NavigationChild {
  id: string
  label: string
  route: string
  available?: boolean
}

interface NavigationItem {
  id: string
  label: string
  icon: string
  route: string
  children?: NavigationChild[]
  available?: boolean
}

const navigationItems: NavigationItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'pi pi-home', route: '/', available: true },
  { id: 'example', label: 'Example', icon: 'pi pi-table', route: '/example', available: true },
  { id: 'components', label: 'Components', icon: 'pi pi-palette', route: '/components', available: true },
]

const isItemActive = (item: NavigationItem): boolean => {
  if (item.children) {
    return item.children.some((child: NavigationChild) => route.path === child.route)
  }
  return route.path === item.route || (item.route !== '/' && route.path.startsWith(item.route + '/'))
}

const isChildActive = (childRoute: string) => {
  return route.path === childRoute
}

const closeSidebar = () => emit('close')
</script>

<template>
  <aside
    class="fixed left-0 bg-white border-r border-slate-200 transition-all duration-300 ease-out overflow-hidden shadow-sm"
    :class="[
      props.open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      props.collapsed ? 'lg:w-16' : 'lg:w-64',
      'w-64',
      'top-0 h-full z-50 lg:top-[73px] lg:h-[calc(100vh-73px)] lg:z-40',
    ]"
  >
    <nav
      class="flex-1 py-6 overflow-y-auto transition-all duration-300 ease-out"
      :class="props.collapsed ? 'lg:px-2' : 'px-4'"
    >
      <div class="space-y-2">
        <template v-for="item in navigationItems">
          <div v-if="!item.children" :key="item.id">
            <NuxtLink
              v-if="item.available !== false"
              :to="item.route"
              class="flex items-center rounded-xl text-slate-700 hover:bg-slate-50 hover:shadow-sm transition-all duration-200 ease-out group relative overflow-hidden"
              :class="[
                isItemActive(item) ? 'bg-slate-50 text-blue-700' : '',
                props.collapsed ? 'lg:justify-center lg:px-3 lg:py-3' : 'gap-3 px-3 py-3',
              ]"
              style="min-height: 44px"
              @click="closeSidebar"
            >
              <i
                :class="[
                  item.icon,
                  'text-lg shrink-0 transition-all duration-200',
                  isItemActive(item) ? 'text-blue-500 bg-blue-100 p-2 rounded-lg' : '',
                ]"
              />
              <span v-if="!props.collapsed" class="font-medium whitespace-nowrap text-sm tracking-wide">
                {{ item.label }}
              </span>
            </NuxtLink>

            <div
              v-else
              class="flex items-center rounded-lg text-slate-400 cursor-not-allowed opacity-60"
              :class="props.collapsed ? 'lg:justify-center lg:px-3 lg:py-3' : 'gap-3 px-4 py-3'"
            >
              <i :class="item.icon" class="text-lg shrink-0 w-5 h-5" />
              <span v-if="!props.collapsed" class="font-medium tracking-wide">
                {{ item.label }}
              </span>
            </div>
          </div>

          <div v-else :key="`${item.id}-children`">
            <div v-if="props.collapsed" class="lg:block hidden">
              <NuxtLink
                v-if="item.available !== false"
                :to="item.route"
                class="flex items-center justify-center px-3 py-3 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors duration-200 ease-out"
                :class="isItemActive(item) ? 'bg-blue-50 text-blue-700' : ''"
                @click="closeSidebar"
              >
                <i :class="item.icon" class="text-lg" />
              </NuxtLink>

              <div
                v-else
                class="flex items-center justify-center px-3 py-3 rounded-lg text-slate-400 cursor-not-allowed opacity-60"
              >
                <i :class="item.icon" class="text-lg" />
              </div>
            </div>

            <div v-else class="transition-all duration-300 ease-out">
              <template v-if="item.available !== false">
                <details class="group" :open="isItemActive(item)">
                  <summary
                    class="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors duration-200 ease-out cursor-pointer list-none overflow-hidden"
                    :class="isItemActive(item) ? 'bg-blue-50 text-blue-700 font-semibold' : ''"
                  >
                    <i :class="item.icon" class="text-lg shrink-0 w-5 h-5" />
                    <span class="flex-1 font-medium whitespace-nowrap tracking-wide">{{ item.label }}</span>
                    <i
                      class="pi pi-chevron-down text-sm transition-transform duration-300 ease-out group-open:rotate-180 shrink-0"
                    />
                  </summary>

                  <div class="mt-1 ml-8 space-y-1 overflow-hidden">
                    <template v-for="child in item.children">
                      <NuxtLink
                        v-if="child.available !== false"
                        :key="child.id"
                        :to="child.route"
                        class="flex items-center px-4 py-2 rounded-lg text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors duration-200 ease-out whitespace-nowrap overflow-hidden"
                        :class="isChildActive(child.route) ? 'bg-blue-50 text-blue-700 font-medium' : ''"
                        @click="closeSidebar"
                      >
                        {{ child.label }}
                      </NuxtLink>

                      <div
                        v-else
                        :key="`${child.id}-disabled`"
                        class="flex items-center px-4 py-2 rounded-lg text-sm text-slate-400 cursor-not-allowed opacity-60 whitespace-nowrap overflow-hidden"
                      >
                        <span class="flex items-center gap-2">
                          {{ child.label }}
                        </span>
                      </div>
                    </template>
                  </div>
                </details>
              </template>

              <div
                v-else
                class="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-400 cursor-not-allowed opacity-60 overflow-hidden"
              >
                <i :class="item.icon" class="text-lg shrink-0 w-5 h-5" />
                <span class="flex-1 font-medium whitespace-nowrap tracking-wide flex items-center gap-2">
                  {{ item.label }}
                </span>
                <i class="pi pi-lock text-sm shrink-0" />
              </div>
            </div>
          </div>
        </template>
      </div>
    </nav>
  </aside>
</template>
