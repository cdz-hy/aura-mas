import type { RouteRecordRaw } from 'vue-router'
import type { Component } from 'vue'
import type { MenuItem } from '@/types/menu'
import { useAuthStore } from '@/stores/auth'

const componentMap: Record<string, () => Promise<Component>> = {
  'dashboard':         () => import('@/views/DashboardView.vue'),
  'plan-list':         () => import('@/views/PlanListView.vue'),
  'note-list':         () => import('@/views/NoteListView.vue'),
  'profile':           () => import('@/views/ProfileView.vue'),
  'admin-dashboard':   () => import('@/views/admin/AdminDashboard.vue'),
  'kb-management':     () => import('@/views/admin/KBManagement.vue'),
  'user-management':   () => import('@/views/admin/UserManagement.vue'),
}

function collectCodes(menus: MenuItem[]): Set<string> {
  const codes = new Set<string>()
  function walk(items: MenuItem[]) {
    for (const item of items) {
      codes.add(item.code)
      if (item.children?.length) walk(item.children)
    }
  }
  walk(menus)
  return codes
}

function buildImplicitRoutes(menuCodes: Set<string>): RouteRecordRaw[] {
  const routes: RouteRecordRaw[] = []

  // Default redirect from / to role's home
  routes.push({
    path: '',
    name: 'Home',
    redirect: () => {
      const authStore = useAuthStore()
      return authStore.homeRoute
    },
  })

  if (menuCodes.has('plan-list')) {
    routes.push({
      path: 'plan/:id',
      name: 'PlanDetail',
      component: () => import('@/views/PlanDetailView.vue'),
      props: true,
    })
  }

  if (menuCodes.has('note-list')) {
    routes.push({
      path: 'notes/:id',
      name: 'NoteDetail',
      component: () => import('@/views/NoteDetailView.vue'),
      props: true,
    })
  }

  // Settings accessible by clicking user avatar in sidebar
  routes.push({
    path: 'settings',
    name: 'UserSettings',
    component: () => import('@/views/UserSettingsView.vue'),
  })

  return routes
}

export function buildRoutes(menus: MenuItem[]): RouteRecordRaw[] {
  const routes: RouteRecordRaw[] = []
  const menuCodes = collectCodes(menus)

  function extract(items: MenuItem[]) {
    for (const menu of items) {
      if (menu.path && componentMap[menu.code]) {
        routes.push({
          path: menu.path.replace(/^\//, ''),
          name: menu.code,
          component: componentMap[menu.code],
          meta: { title: menu.name },
        })
      }
      if (menu.children?.length) {
        extract(menu.children)
      }
    }
  }

  extract(menus)
  routes.push(...buildImplicitRoutes(menuCodes))

  routes.push({
    path: ':pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
  })

  return routes
}
