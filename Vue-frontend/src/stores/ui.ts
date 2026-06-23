import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false)
  const notesPanelOpen = ref(false)
  const tutorPanelOpen = ref(false)
  const currentTheme = ref<'light'>('light')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleNotesPanel() {
    tutorPanelOpen.value = false
    notesPanelOpen.value = !notesPanelOpen.value
  }

  function toggleTutorPanel() {
    notesPanelOpen.value = false
    tutorPanelOpen.value = !tutorPanelOpen.value
  }

  return { sidebarCollapsed, notesPanelOpen, tutorPanelOpen, currentTheme, toggleSidebar, toggleNotesPanel, toggleTutorPanel }
})
