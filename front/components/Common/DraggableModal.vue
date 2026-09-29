<script lang="ts" setup>
import { ref, computed, onUnmounted } from 'vue'

interface DraggableModalProps {
  visible: boolean
  title: string
  subtitle?: string
  width?: string
  height?: string
  loading?: boolean
  hideConfirm?: boolean
  hideCancel?: boolean
  confirmText?: string
  cancelText?: string
  confirmSeverity?: string
  actions?: any[]
}

const props = defineProps<DraggableModalProps>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  close: []
  confirm: []
}>()

const modalRef = ref<HTMLElement>()
const dragHandleRef = ref<HTMLElement>()
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })
const position = ref({ x: 0, y: 0 })

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => {
    emit('update:visible', value)
    if (!value) {
      emit('close')
      position.value = { x: 0, y: 0 }
    }
  },
})

const handleMouseDown = (e: MouseEvent) => {
  if (!modalRef.value) return

  isDragging.value = true
  const rect = modalRef.value.getBoundingClientRect()
  dragOffset.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  e.preventDefault()
}

const handleMouseMove = (e: MouseEvent) => {
  if (!isDragging.value || !modalRef.value) return

  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const modalWidth = modalRef.value.offsetWidth
  const modalHeight = modalRef.value.offsetHeight

  let newX = e.clientX - dragOffset.value.x - viewportWidth / 2 + modalWidth / 2
  let newY = e.clientY - dragOffset.value.y - viewportHeight / 2 + modalHeight / 2

  // Keep modal within viewport bounds
  newX = Math.max(-modalWidth / 2 + 50, Math.min(newX, modalWidth / 2 - 50))
  newY = Math.max(-modalHeight / 2 + 50, Math.min(newY, modalHeight / 2 - 50))

  position.value = { x: newX, y: newY }
}

const handleMouseUp = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

const handleConfirm = () => {
  emit('confirm')
}

const handleClose = () => {
  dialogVisible.value = false
}

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    handleClose()
  }
}

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="dialogVisible"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 transition-opacity duration-300"
      @click="handleBackdropClick"
    >
      <div
        ref="modalRef"
        class="draggable-modal bg-white rounded-lg shadow-xl border border-slate-200 flex flex-col"
        :style="{
          width: width || '800px',
          height: height || 'auto',
          maxHeight: '90vh',
          minWidth: '400px',
          transform: `translate(${position.x}px, ${position.y}px)`,
          transition: isDragging ? 'none' : 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        }"
      >
        <div
          ref="dragHandleRef"
          class="flex items-center justify-between bg-white px-5 py-4 rounded-t-xl cursor-move border-b border-slate-100 transition-colors hover:bg-slate-50/50"
          @mousedown="handleMouseDown"
        >
          <div class="flex items-center gap-2">
            <i class="pi pi-bars text-slate-400 text-sm" />
          </div>
          <Button
            icon="pi pi-times"
            severity="secondary"
            text
            rounded
            size="small"
            class="!text-slate-400 hover:!text-slate-600 hover:!bg-slate-100 w-8 h-8 !p-0"
            @click="handleClose"
          />
        </div>

        <div class="flex-1 overflow-hidden flex flex-col">
          <div v-if="title" class="px-8 pt-8 pb-6">
            <h2 class="text-xl font-bold text-slate-900 tracking-tight">{{ title }}</h2>
            <p v-if="subtitle" class="text-sm text-slate-500 mt-1 font-medium">{{ subtitle }}</p>
          </div>

          <div class="flex-1 overflow-y-auto px-8 custom-scrollbar">
            <slot />
          </div>

          <div class="border-t border-slate-100 bg-slate-50/50 px-8 py-5 rounded-b-xl mt-auto">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div v-if="loading" class="flex items-center gap-2">
                  <i class="pi pi-spin pi-spinner text-blue-500 text-sm" />
                  <span class="text-sm text-slate-600">Processing...</span>
                </div>
                <template v-if="actions">
                  <Button
                    v-for="(action, index) in actions"
                    :key="index"
                    :label="action.label"
                    :icon="action.icon"
                    :severity="action.severity || 'secondary'"
                    :outlined="action.outlined !== false"
                    size="small"
                    @click="action.handler"
                  />
                </template>
              </div>
              <div class="flex items-center gap-3">
                <Button
                  v-if="!hideCancel"
                  :label="cancelText || 'Close'"
                  severity="secondary"
                  text
                  size="small"
                  class="!px-4"
                  @click="handleClose"
                />
                <Button
                  v-if="!hideConfirm"
                  :label="confirmText || 'Save'"
                  :severity="confirmSeverity || 'primary'"
                  size="small"
                  :loading="loading"
                  :disabled="loading"
                  class="!px-5 shadow-sm shadow-blue-500/20"
                  @click="handleConfirm"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.draggable-modal {
  user-select: none;
  max-width: 95vw;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

/* Smooth cursor transitions */
.cursor-move:active {
  cursor: grabbing;
}

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}
</style>
