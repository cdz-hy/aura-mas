import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MenuItem } from '@/types/menu'
import router from '@/router'
import { buildRoutes } from '@/config/routeComponents'

const IMPLICIT_ROUTE_NAMES = new Set(['PlanDetail', 'NoteDetail', 'UserSettings'])

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

  const allowedRouteNames = computed(() => {
    const names = new Set(flatMenuCodes.value)
    IMPLICIT_ROUTE_NAMES.forEach(n => names.add(n))
    return names
  })

  function generateRoutes(menuItems: MenuItem[]) {
    menus.value = menuItems
    localStorage.setItem('menus', JSON.stringify(menuItems))

    const existingNames = new Set(router.getRoutes().map(r => r.name))
    const routes = buildRoutes(menuItems)
    routes.forEach(route => {
      if (!existingNames.has(route.name)) {
        router.addRoute('Root', route)
      }
    })
    // 添加 404 兜底路由（必须在所有动态路由之后）
    if (!existingNames.has('NotFound')) {
      router.addRoute('Root', {
        path: ':pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('@/views/NotFoundView.vue'),
      })
    }
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

  return { menus, flatMenuCodes, allowedRouteNames, routesAdded, generateRoutes, resetRoutes, restoreMenus }
})
