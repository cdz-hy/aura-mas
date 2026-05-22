import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MenuItem } from '@/types/menu'
import router from '@/router'
import { buildRoutes } from '@/config/routeComponents'

export const usePermissionStore = defineStore('permission', () => {
  const menus = ref<MenuItem[]>([])
  const routesAdded = ref(false)

  const flatMenuCodes = computed(() => {
    const codes = new Set<string>()
    function walk(items: MenuItem[]) {
      for (const item of items) {
        codes.add(item.code)
        if (item.children?.length) walk(item.children)
      }
    }
    walk(menus.value)
    return codes
  })

  function generateRoutes(menuItems: MenuItem[]) {
    menus.value = menuItems
    localStorage.setItem('menus', JSON.stringify(menuItems))

    const routes = buildRoutes(menuItems)
    routes.forEach(route => {
      router.addRoute('Root', route)
    })
    routesAdded.value = true
  }

  function resetRoutes() {
    menus.value = []
    routesAdded.value = false
    localStorage.removeItem('menus')
  }

  function restoreMenus(): boolean {
    if (routesAdded.value) return true
    try {
      const saved = localStorage.getItem('menus')
      if (saved) {
        const menuItems = JSON.parse(saved)
        if (menuItems?.length) {
          generateRoutes(menuItems)
          return true
        }
      }
    } catch { /* ignore */ }
    return false
  }

  return { menus, flatMenuCodes, routesAdded, generateRoutes, resetRoutes, restoreMenus }
})
