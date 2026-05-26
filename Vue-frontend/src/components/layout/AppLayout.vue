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
      <main class="flex-1 overflow-y-auto bg-paper">
        <div class="max-w-7xl mx-auto px-6 py-8">
          <router-view v-slot="{ Component }">
            <transition name="page-fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>

    <!-- Notes panel (slide-in from right) -->
    <transition name="slide-right">
      <div v-if="uiStore.notesPanelOpen" class="w-[360px] border-l border-navy-100 bg-white flex-shrink-0 overflow-hidden">
        <NoteSidebar />
      </div>
    </transition>

  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import NoteSidebar from '@/components/note/NoteSidebar.vue'
import Toast from '@/components/common/Toast.vue'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
</script>

<style scoped>
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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
