<script setup lang="ts">
import ContactForm from '~/components/Auth/ContactForm.vue'
definePageMeta({ layout: 'planner', middleware: 'guest' })
</script>

<template>
  <ContactForm mode="login" />
</template>
