import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { type User } from 'oidc-client-ts'
import { getUser, logout as authLogout, isPublicAccessEnabled } from '../auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!user.value && !user.value.expired)
  const isReadOnly = computed(() => isPublicAccessEnabled() && !isAuthenticated.value)
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

  return { user, isAuthenticated, isReadOnly, username, accessToken, init, setUser, logout }
})
