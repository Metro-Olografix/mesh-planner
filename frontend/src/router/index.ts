import { createRouter, createWebHistory } from 'vue-router'
import { getUser, isPublicAccessEnabled } from '../auth'
import HomeView from '../views/HomeView.vue'
import CallbackView from '../views/CallbackView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/callback',
      name: 'callback',
      component: CallbackView,
    },
    {
      path: '/try',
      name: 'try-coverage',
      component: () => import('../views/TryCoverageView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true
  const user = await getUser()
  if (!user || user.expired) {
    if (isPublicAccessEnabled()) {
      // Allow unauthenticated through — components will render in read-only mode
      return true
    }
    const { login } = await import('../auth')
    await login()
    return false
  }
  // Populate the store before the route component mounts so token() is never
  // null on the first API call. App.vue's onMounted init() is a no-op after this.
  const { useAuthStore } = await import('../stores/auth')
  const authStore = useAuthStore()
  if (!authStore.user) authStore.setUser(user)
  return true
})

export default router
