import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LearningPlan, LearningResource } from '@/types/plan'

export const usePlanStore = defineStore('plan', () => {
  const plans = ref<LearningPlan[]>([])
  const currentPlan = ref<LearningPlan | null>(null)
  const currentResources = ref<LearningResource[]>([])
  const loading = ref(false)

  const totalPlans = computed(() => plans.value.length)
  const completedPlans = computed(() => plans.value.filter(p => p.status === 4).length)

  function setPlans(data: LearningPlan[]) {
    plans.value = data
  }

  function setCurrentPlan(plan: LearningPlan | null) {
    currentPlan.value = plan
  }

  function setCurrentResources(resources: LearningResource[]) {
    currentResources.value = resources
  }

  function updatePlanProgress(planId: number, progress: number) {
    const plan = plans.value.find(p => p.id === planId)
    if (plan) plan.progress = progress
    if (currentPlan.value?.id === planId) {
      currentPlan.value.progress = progress
    }
  }

  return {
    plans, currentPlan, currentResources, loading,
    totalPlans, completedPlans,
    setPlans, setCurrentPlan, setCurrentResources, updatePlanProgress,
  }
})
