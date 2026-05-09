import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
      },
      {
        path: 'plan/create',
        name: 'PlanList',
        component: () => import('@/views/PlanListView.vue'),
      },
      {
        path: 'plan/:id',
        name: 'PlanDetail',
        component: () => import('@/views/PlanDetailView.vue'),
        props: true,
      },
      {
        path: 'notes',
        name: 'Notes',
        component: () => import('@/views/NoteListView.vue'),
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/ProfileView.vue'),
      },
      {
        path: 'admin',
        meta: { requiresRole: 'admin' },
        children: [
          {
            path: '',
            name: 'AdminDashboard',
            component: () => import('@/views/admin/AdminDashboard.vue'),
          },
          {
            path: 'kb',
            name: 'KBManagement',
            component: () => import('@/views/admin/KBManagement.vue'),
          },
          {
            path: 'users',
            name: 'UserManagement',
            component: () => import('@/views/admin/UserManagement.vue'),
          },
        ],
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else if (to.meta.guest && authStore.isLoggedIn) {
    next('/dashboard')
  } else if (to.meta.requiresRole && authStore.user?.role !== to.meta.requiresRole) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
