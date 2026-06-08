import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false)
  const notesPanelOpen = ref(false)
  const currentTheme = ref<'light'>('light')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleNotesPanel() {
    notesPanelOpen.value = !notesPanelOpen.value
  }

  return { sidebarCollapsed, notesPanelOpen, currentTheme, toggleSidebar, toggleNotesPanel }
})
