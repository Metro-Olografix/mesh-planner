import { createRouter, createWebHistory } from 'vue-router'
import { getUser } from '../auth'
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
  ],
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true
  const user = await getUser()
  if (!user || user.expired) {
    const { login } = await import('../auth')
    await login()
    return false
  }
  return true
})

export default router
