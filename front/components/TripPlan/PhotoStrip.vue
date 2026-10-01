<script setup lang="ts">
import type { ImageCredit } from '~/types/trip-plan'

defineProps<{
  photos: ImageCredit[]
  alt: string
  enlargeLabel: string
  /** Kept for callers; strip scroll arrows are not shown outside the lightbox. */
  backLabel?: string
  forwardLabel?: string
  thumbClass?: string
}>()

const emit = defineEmits<{ open: [photo: ImageCredit] }>()
</script>

<template>
  <div v-if="photos.length" class="min-w-0">
    <div class="flex gap-2 overflow-x-auto scroll-smooth">
      <button
        v-for="photo in photos"
        :key="photo.url"
        type="button"
        class="shrink-0 cursor-zoom-in"
        :aria-label="enlargeLabel"
        @click.stop="emit('open', photo)"
      >
        <img
          :src="photo.url"
          :alt="alt"
          :class="thumbClass || 'h-24 w-36'"
          class="rounded-inner object-cover"
          loading="lazy"
        />
      </button>
    </div>
  </div>
</template>
