<template>
  <div class="d-flex align-items-center justify-content-center vh-100">
    <div class="text-center">
      <div class="spinner-border text-primary mb-3" role="status"></div>
      <p class="text-muted">{{ $t('auth.completing_login') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { handleCallback } from '../auth'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  try {
    const user = await handleCallback()
    authStore.setUser(user)
    await router.push('/')
  } catch (e) {
    console.error('Auth callback failed', e)
    await router.push('/')
  }
})
</script>
