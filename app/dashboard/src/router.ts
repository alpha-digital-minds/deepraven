import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = createRouter({
  history: createWebHistory('/dashboard/'),
  linkActiveClass: 'active',
  linkExactActiveClass: 'active',
  routes: [
    {
      path: '/login',
      component: () => import('./components/LoginScreen.vue'),
    },
    {
      path: '/',
      component: () => import('./components/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', component: () => import('./components/HomeDashboard.vue') },
        { path: 'projects/:projectId', component: () => import('./components/ProjectPanel.vue') },
        {
          path: 'projects/:projectId/contacts/:contactId',
          component: () => import('./components/ContactDetail.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(to => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
