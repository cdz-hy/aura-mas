import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'

export { resolveNoteCaptureSource } from '@/stores/noteCapture'
export type { NoteCaptureSource, NoteCaptureMode, NoteCaptureRequest } from '@/stores/noteCapture'

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

  // 未登录用户：需要认证的页面跳转登录
  if (!authStore.isLoggedIn) {
    if (to.meta.requiresAuth || (!to.meta.guest && to.name !== 'Login' && to.name !== 'Register')) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    next()
    return
  }

  // 已登录用户访问 guest 页面（登录/注册）→ 跳转首页
  if (to.meta.guest) {
    next(authStore.homeRoute)
    return
  }

  // 已登录但路由尚未恢复 → 从 localStorage 恢复
  if (!permissionStore.routesAdded) {
    const restored = permissionStore.restoreMenus()
    if (!restored) {
      authStore.logout()
      next('/login')
      return
    }
    next({ ...to, replace: true })
    return
  }

  // 路由已就绪：检查权限
  const routeName = to.name as string | undefined
  if (routeName && !permissionStore.allowedRouteNames.has(routeName)) {
    // 有效路由但无权限 → 跳转首页
    next(authStore.homeRoute)
    return
  }

  if (!routeName && to.matched.length > 0) {
    // 匹配到 NotFound 兜底路由 → 放行（显示 404 页面）
    next()
    return
  }

  if (!routeName) {
    // 完全未匹配 → 404
    next({ name: 'NotFound', replace: true })
    return
  }

  next()
})

export default router
