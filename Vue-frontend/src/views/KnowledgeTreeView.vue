<template>
  <div class="flex h-full items-center justify-center text-sm text-navy-400">
    正在打开知识树...
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const planId = route.params.planId || route.params.id
  if (planId) {
    router.replace({
      name: 'PlanDetail',
      params: { id: planId },
      query: { ...route.query, view: 'tree' },
    })
  } else {
    router.replace('/plan/create')
  }
})
</script>
