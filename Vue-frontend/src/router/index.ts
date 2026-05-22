import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Root',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const permissionStore = usePermissionStore()

  if (to.meta.guest && authStore.isLoggedIn) {
    next(authStore.homeRoute)
    return
  }

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  if (authStore.isLoggedIn && !permissionStore.routesAdded) {
    const restored = permissionStore.restoreMenus()
    if (!restored) {
      authStore.logout()
      next('/login')
      return
    }
    next({ ...to, replace: true })
    return
  }

  next()
})

export default router
