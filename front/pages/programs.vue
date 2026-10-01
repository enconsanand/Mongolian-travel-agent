<script setup lang="ts">
definePageMeta({ layout: 'planner', auth: false })

await navigateTo({ path: '/', hash: '#events' }, { replace: true })
</script>
