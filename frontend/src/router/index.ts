import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/NotificationsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/notifications/:id',
      name: 'notification-detail',
      component: () => import('@/views/NotificationDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'admin',
      redirect: '/admin/users',
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { 
        requiresAuth: true,
        requiresPermission: 'user:manage'
      }
    },
    {
      path: '/admin/organization',
      name: 'admin-organization',
      component: () => import('@/views/admin/OrganizationView.vue'),
      meta: { 
        requiresAuth: true,
        requiresPermission: 'organization:manage'
      }
    },
    {
      path: '/admin/targets',
      name: 'admin-targets',
      component: () => import('@/views/admin/TargetsView.vue'),
      meta: { 
        requiresAuth: true,
        requiresPermission: 'target:manage'
      }
    },
    {
      path: '/admin/endpoints',
      name: 'admin-endpoints',
      component: () => import('@/views/admin/EndpointsView.vue'),
      meta: { 
        requiresAuth: true,
        requiresPermission: 'endpoint:manage'
      }
    },
    {
      path: '/audit-logs',
      name: 'audit-logs',
      component: () => import('@/views/AuditLogsView.vue'),
      meta: { 
        requiresAuth: true,
        requiresPermission: 'audit:view'
      }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue')
    }
  ]
})

// Navigation guards
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  
  // Check if route requires authentication
  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      // Redirect to login with return path
      next({
        name: 'login',
        query: { redirect: to.fullPath }
      })
      return
    }

    // Check for specific permission requirements
    if (to.meta.requiresPermission) {
      const requiredPermission = to.meta.requiresPermission as string
      if (!authStore.hasPermission(requiredPermission)) {
        // Redirect to dashboard if user lacks permission
        next({ name: 'dashboard' })
        return
      }
    }
  }

  // If user is authenticated and trying to access login, redirect to dashboard
  if (to.name === 'login' && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
    return
  }

  next()
})

export default router
