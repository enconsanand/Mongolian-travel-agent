<script setup lang="ts">
import type { HeroSlide } from '~/constants/heroSlides'

/**
 * The hero picture: a photo in a frame, with brand-coloured shapes behind it. Each slide has its own composition.
 * The licence credit sits behind a small info mark: CC BY needs it reachable, not shouting.
 */
const { slide, alt, credit } = defineProps<{
  slide: HeroSlide
  alt: string
  credit: string
}>()
</script>

<template>
  <div class="hero-showcase relative mx-auto aspect-[4/5] w-full max-w-md">
    <Transition name="hero-swap" mode="out-in">
      <div :key="slide.id" class="absolute inset-0" :data-layout="slide.layout">
        <!-- Colour shapes behind the photo -->
        <template v-if="slide.layout === 'orbit'">
          <span class="shape absolute top-[10%] -right-[10%] h-[34%] w-[100%] -rotate-[38deg] rounded-[50%] bg-brand" />
          <span
            class="shape absolute bottom-[14%] -left-[8%] h-[20%] w-[66%] -rotate-[38deg] rounded-[50%] bg-accent"
          />
        </template>
        <template v-else-if="slide.layout === 'sun'">
          <span class="shape absolute top-[2%] -right-[4%] aspect-square w-[60%] rounded-full bg-accent" />
          <span class="shape absolute bottom-[6%] -left-[4%] h-[3px] w-[60%] bg-brand" />
        </template>
        <template v-else>
          <span class="shape absolute top-[10%] -left-[6%] h-[80%] w-[60%] rounded-t-full bg-success/80" />
          <span class="shape absolute -right-[2%] bottom-[10%] aspect-square w-[30%] rounded-full bg-brand" />
        </template>

        <img
          :src="slide.image"
          :alt="alt"
          class="hero-photo absolute inset-[6%] h-[88%] w-[88%] object-cover shadow-card"
          :class="{
            'rounded-card': slide.layout === 'orbit',
            'rounded-full': slide.layout === 'sun',
          }"
          :style="{ objectPosition: slide.focus }"
        />
      </div>
    </Transition>
    <a
      :href="slide.source"
      target="_blank"
      rel="noopener noreferrer"
      class="absolute right-0 bottom-0 grid h-7 w-7 place-items-center rounded-full bg-surface/80 text-ink-subtle backdrop-blur transition-colors hover:text-ink"
      :title="credit"
      :aria-label="credit"
    >
      <i class="pi pi-info-circle text-xs" aria-hidden="true" />
    </a>
  </div>
</template>

<style scoped>
[data-layout='orbit'] .hero-photo {
  inset: 4% 16%;
  height: 92%;
  width: 68%;
}

[data-layout='sun'] .hero-photo {
  inset: 14% 6%;
  height: auto;
  width: 88%;
  aspect-ratio: 1;
}

[data-layout='arch'] .hero-photo {
  inset: 10% 8%;
  height: 80%;
  width: 84%;
  border-radius: 999px 999px var(--radius-card) var(--radius-card);
}

.shape {
  animation: hero-shape-in 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}

.hero-swap-enter-active,
.hero-swap-leave-active {
  transition:
    opacity 0.35s ease,
    translate 0.35s ease;
}

.hero-swap-enter-from {
  opacity: 0;
  translate: 24px 0;
}

.hero-swap-leave-to {
  opacity: 0;
  translate: -24px 0;
}

@keyframes hero-shape-in {
  from {
    opacity: 0;
    scale: 0.85;
  }
}

@media (prefers-reduced-motion: reduce) {
  .shape {
    animation: none;
  }

  .hero-swap-enter-active,
  .hero-swap-leave-active {
    transition: none;
  }
}
</style>
