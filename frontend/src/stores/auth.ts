import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { type User } from 'oidc-client-ts'
import { getUser, logout as authLogout } from '../auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!user.value && !user.value.expired)
  const username = computed(
    () =>
      user.value?.profile?.preferred_username ??
      (user.value?.profile as any)?.name ??
      user.value?.profile?.email ??
      'Unknown'
  )
  const accessToken = computed(() => user.value?.access_token ?? null)

  async function init() {
    user.value = await getUser()
  }

  function setUser(u: User) {
    user.value = u
  }

  async function logout() {
    await authLogout()
    user.value = null
  }

  return { user, isAuthenticated, username, accessToken, init, setUser, logout }
})
