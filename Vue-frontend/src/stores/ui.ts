import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeId = 'light' | 'dark' | 'ocean' | 'forest' | 'sunset'

export interface ThemePreset {
  id: ThemeId
  name: string
  description: string
  preview: { bg: string; accent: string; text: string }
}

export const themePresets: ThemePreset[] = [
  {
    id: 'light',
    name: '清晨白',
    description: '清爽明亮的默认主题',
    preview: { bg: '#fefdfb', accent: '#4164b2', text: '#0d1424' },
  },
  {
    id: 'dark',
    name: '深夜蓝',
    description: '护眼暗色主题',
    preview: { bg: '#131720', accent: '#3d6090', text: '#e8ecf4' },
  },
  {
    id: 'ocean',
    name: '海洋蓝',
    description: '清新海洋色调',
    preview: { bg: '#f5fafd', accent: '#2891cc', text: '#081d29' },
  },
  {
    id: 'forest',
    name: '森林绿',
    description: '自然绿色主题',
    preview: { bg: '#fafbf5', accent: '#388838', text: '#0b1c0b' },
  },
  {
    id: 'sunset',
    name: '暖阳橙',
    description: '温暖夕阳色调',
    preview: { bg: '#fffbf5', accent: '#d86020', text: '#381406' },
  },
]

// Dark mode CSS overrides injected as a <style> tag for maximum cascade priority
const DARK_OVERRIDES_CSS = `
/* === DARK MODE OVERRIDES (injected at end of <head> for cascade priority) === */

/* Body */
body {
  background-color: var(--color-bg) !important;
  color: var(--color-text) !important;
}

/* Paper background */
.bg-paper {
  background-color: var(--color-bg-paper) !important;
}

/* White surfaces - covers all card variants and plain white backgrounds */
.bg-white,
.card,
.card-hover,
.stat-card,
[class*="bg-white"] {
  background-color: var(--color-surface) !important;
}
.card,
.card-hover,
.stat-card {
  border-color: var(--color-border) !important;
}

/* Header and sidebar */
header, header[class*="bg-white"] {
  background-color: rgba(22, 26, 36, 0.85) !important;
  border-color: var(--color-border) !important;
}

aside, aside[class*="bg-white"] {
  background-color: var(--cream-50) !important;
}

aside .bg-white, aside .flex-shrink-0 {
  background-color: var(--cream-50) !important;
}

/* ALL inputs - aggressive override */
input, textarea, select {
  background-color: var(--cream-100) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text) !important;
}

input::placeholder, textarea::placeholder {
  color: var(--color-text-muted) !important;
}

input:disabled, textarea:disabled {
  background-color: var(--cream-200) !important;
  color: var(--navy-400) !important;
}

/* Input field class */
.input-field {
  background-color: var(--cream-100) !important;
  border-color: var(--color-border) !important;
  color: var(--color-text) !important;
}

/* Borders */
.border-navy-100, .border-navy-200 {
  border-color: var(--color-border) !important;
}
.border-navy-100\\/50, .border-navy-200\\/50, .border-navy-100\\/60 {
  border-color: var(--color-border-light) !important;
}

/* Buttons */
.btn-primary {
  background-color: #3d6090 !important;
  color: #fff !important;
}
.btn-primary:hover {
  background-color: #4a70a4 !important;
}
.btn-secondary {
  background-color: var(--color-surface) !important;
  color: var(--navy-700) !important;
  border-color: var(--color-border) !important;
}
.btn-secondary:hover {
  background-color: var(--cream-100) !important;
}
.btn-ghost {
  color: var(--navy-500) !important;
}
.btn-ghost:hover {
  background-color: var(--cream-100) !important;
}

/* Active button states */
.bg-navy-600, .bg-navy-700 {
  background-color: #3d6090 !important;
}
.hover\\:bg-navy-700:hover {
  background-color: #4a70a4 !important;
}
.hover\\:bg-navy-50:hover {
  background-color: var(--cream-100) !important;
}

/* Sidebar */
.sidebar-link-active {
  background-color: rgba(38, 48, 64, 0.8) !important;
  color: var(--navy-800) !important;
}

/* Badge color overrides */
.bg-blue-50, .badge-doc { background-color: rgba(59,130,246,0.12) !important; }
.bg-emerald-50, .badge-code { background-color: rgba(16,185,129,0.12) !important; }
.bg-amber-50, .badge-quiz { background-color: rgba(245,158,11,0.12) !important; }
.bg-purple-50, .badge-mindmap { background-color: rgba(139,92,246,0.12) !important; }
.bg-rose-50, .badge-reading { background-color: rgba(244,63,94,0.12) !important; }
.bg-sky-50 { background-color: rgba(14,165,233,0.12) !important; }
.bg-indigo-50 { background-color: rgba(99,102,241,0.12) !important; }
.bg-teal-50 { background-color: rgba(20,184,166,0.12) !important; }
.bg-orange-50 { background-color: rgba(249,115,22,0.12) !important; }
.bg-pink-50 { background-color: rgba(236,72,153,0.12) !important; }
.bg-cyan-50 { background-color: rgba(6,182,212,0.12) !important; }
.bg-violet-50 { background-color: rgba(139,92,246,0.12) !important; }
.bg-red-50 { background-color: rgba(239,68,68,0.12) !important; }
.bg-red-500 { background-color: #dc2626 !important; }

.text-blue-500, .text-blue-600, .text-blue-700 { color: #93bbfc !important; }
.text-emerald-500, .text-emerald-600, .text-emerald-700 { color: #6ee7b7 !important; }
.text-amber-500, .text-amber-600, .text-amber-700 { color: #fcd488 !important; }
.text-purple-500, .text-purple-600, .text-purple-700 { color: #c4b5fd !important; }
.text-rose-500, .text-rose-600, .text-rose-700 { color: #fda4af !important; }
.text-red-400, .text-red-500, .text-red-600 { color: #fca5a5 !important; }

.border-blue-200 { border-color: rgba(59,130,246,0.25) !important; }
.border-emerald-200 { border-color: rgba(16,185,129,0.25) !important; }
.border-amber-200 { border-color: rgba(245,158,11,0.25) !important; }
.border-purple-200 { border-color: rgba(139,92,246,0.25) !important; }
.border-rose-200 { border-color: rgba(244,63,94,0.25) !important; }
.border-red-200 { border-color: rgba(239,68,68,0.25) !important; }
.border-purple-200\\/50 { border-color: rgba(192,132,252,0.2) !important; }

/* Opacity-modified backgrounds */
.bg-navy-50\\/50 { background-color: color-mix(in srgb, var(--navy-50) 50%, transparent) !important; }
.bg-navy-50\\/60 { background-color: color-mix(in srgb, var(--navy-50) 60%, transparent) !important; }
.bg-navy-100\\/50 { background-color: color-mix(in srgb, var(--navy-100) 50%, transparent) !important; }
.bg-navy-100\\/60 { background-color: color-mix(in srgb, var(--navy-100) 60%, transparent) !important; }
.bg-navy-100\\/70 { background-color: color-mix(in srgb, var(--navy-100) 70%, transparent) !important; }

/* Hover states */
.hover\\:bg-navy-50\\/50:hover { background-color: color-mix(in srgb, var(--navy-50) 50%, transparent) !important; }
.hover\\:bg-navy-50\\/60:hover { background-color: color-mix(in srgb, var(--navy-50) 60%, transparent) !important; }
.hover\\:bg-navy-100\\/60:hover { background-color: color-mix(in srgb, var(--navy-100) 60%, transparent) !important; }
.hover\\:bg-red-50:hover { background-color: rgba(239,68,68,0.12) !important; }
.hover\\:bg-red-600:hover { background-color: #b91c1c !important; }
.hover\\:bg-emerald-50:hover { background-color: rgba(16,185,129,0.1) !important; }

/* Gray overrides */
.bg-gray-50, .bg-gray-100 { background-color: var(--cream-100) !important; }
.bg-gray-200 { background-color: var(--cream-200) !important; }
.border-gray-100, .border-gray-200, .border-gray-300 { border-color: var(--color-border) !important; }
.text-gray-500, .text-gray-600 { color: var(--navy-400) !important; }
.text-gray-700, .text-gray-800 { color: var(--navy-700) !important; }

/* Focus rings */
.focus\\:ring-navy-100:focus { --tw-ring-color: rgba(38,48,64,0.5) !important; }
.focus\\:border-navy-400:focus { border-color: var(--navy-400) !important; }
.focus\\:border-navy-200:focus { border-color: var(--navy-300) !important; }

/* Scrollbar */
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb) !important; }
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover) !important; }

/* Selection */
::selection { background: var(--selection-bg) !important; color: var(--selection-color) !important; }

/* Toast */
.toast { background-color: var(--color-surface) !important; border-color: var(--color-border) !important; color: var(--color-text) !important; }

/* Markdown */
.markdown-body h1, .markdown-body h2, .markdown-body h3 { color: var(--color-text); }
.markdown-body code { background: var(--color-border-light); }
.markdown-body pre { background: var(--navy-800); color: var(--cream-100); }
.markdown-body th, .markdown-body td { border-color: var(--color-border); }
.markdown-body th { background: var(--color-border-light); }
.markdown-body a { color: var(--navy-500); }
.markdown-body a:hover { color: var(--navy-700); }
.markdown-body hr { border-top-color: var(--color-border); }
`

let darkStyleEl: HTMLStyleElement | null = null

function injectDarkStyles() {
  if (darkStyleEl) return
  darkStyleEl = document.createElement('style')
  darkStyleEl.id = 'dark-theme-overrides'
  darkStyleEl.textContent = DARK_OVERRIDES_CSS
  document.head.appendChild(darkStyleEl)
}

function removeDarkStyles() {
  if (darkStyleEl) {
    darkStyleEl.remove()
    darkStyleEl = null
  }
}

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(localStorage.getItem('aura-sidebar-collapsed') === 'true')
  const notesPanelOpen = ref(false)
  const tutorPanelOpen = ref(false)
  const advisorPanelOpen = ref(false)
  const currentTheme = ref<ThemeId>('light')

  function applyTheme(theme: ThemeId) {
    // Add transition class for smooth color change
    document.documentElement.classList.add('theme-transition')

    // Apply theme attribute (for CSS variable selection)
    document.documentElement.setAttribute('data-theme', theme)
    currentTheme.value = theme

    // For dark mode, inject override styles at end of <head>
    // This guarantees they win the CSS cascade over Tailwind's @layer utilities
    if (theme === 'dark') {
      injectDarkStyles()
    } else {
      removeDarkStyles()
    }

    // Save to localStorage
    localStorage.setItem('aura-theme', theme)

    // Remove transition class after animation
    setTimeout(() => {
      document.documentElement.classList.remove('theme-transition')
    }, 500)
  }

  function setTheme(theme: ThemeId) {
    applyTheme(theme)
  }

  function restoreTheme() {
    const saved = localStorage.getItem('aura-theme') as ThemeId | null
    if (saved && themePresets.some(t => t.id === saved)) {
      applyTheme(saved)
    } else {
      applyTheme('light')
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('aura-sidebar-collapsed', String(sidebarCollapsed.value))
  }

  function toggleNotesPanel() {
    tutorPanelOpen.value = false
    advisorPanelOpen.value = false
    notesPanelOpen.value = !notesPanelOpen.value
  }

  function toggleTutorPanel() {
    notesPanelOpen.value = false
    advisorPanelOpen.value = false
    tutorPanelOpen.value = !tutorPanelOpen.value
  }

  function toggleAdvisorPanel() {
    notesPanelOpen.value = false
    tutorPanelOpen.value = false
    advisorPanelOpen.value = !advisorPanelOpen.value
  }

  return {
    sidebarCollapsed, notesPanelOpen, tutorPanelOpen, advisorPanelOpen, currentTheme,
    toggleSidebar, toggleNotesPanel, toggleTutorPanel, toggleAdvisorPanel,
    setTheme, restoreTheme, applyTheme,
  }
})
