<template>
  <div class="flex h-screen overflow-hidden bg-cream-50">
    <!-- Global Toast -->
    <Toast />
    <!-- Sidebar -->
    <AppSidebar />

    <!-- Main content area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <AppHeader />

      <!-- Page content -->
      <main class="flex-1 bg-paper relative flex flex-col overflow-hidden">
        <router-view v-slot="{ Component, route }">
          <transition name="page-fade" mode="out-in">
            <div :key="String(route.name)" class="w-full h-full" :class="route.meta.fullWidth ? 'flex flex-col p-4 overflow-hidden' : 'overflow-y-auto'">
              <div :class="route.meta.fullWidth ? 'w-full h-full flex flex-col' : 'max-w-7xl mx-auto px-6 py-8 w-full min-h-full'">
                <component :is="Component" />
              </div>
            </div>
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Notes panel (slide-in from right) -->
    <transition name="slide-right">
      <div v-if="uiStore.notesPanelOpen" class="w-[360px] border-l border-navy-100 bg-white flex-shrink-0 overflow-hidden">
        <NoteSidebar />
      </div>
    </transition>

    <!-- Tutor panel (slide-in from right) -->
    <transition name="slide-right">
      <div v-if="uiStore.tutorPanelOpen" class="w-[360px] border-l border-purple-200/50 bg-white flex-shrink-0 overflow-hidden">
        <TutorChatPanel />
      </div>
    </transition>

    <!-- Advisor panel (slide-in from right) -->
    <transition name="slide-right">
      <div v-if="uiStore.advisorPanelOpen" class="w-[360px] border-l border-emerald-200/50 bg-white flex-shrink-0 overflow-hidden">
        <PlanAdvisorChat :is-sidebar="true" @close="uiStore.advisorPanelOpen = false" />
      </div>
    </transition>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import NoteSidebar from '@/components/note/NoteSidebar.vue'
import TutorChatPanel from '@/components/chat/TutorChatPanel.vue'
import PlanAdvisorChat from '@/components/plan/PlanAdvisorChat.vue'
import Toast from '@/components/common/Toast.vue'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const uiStore = useUiStore()

</script>

<style scoped>
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), filter 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.995);
  filter: blur(4px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.995);
  filter: blur(4px);
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
