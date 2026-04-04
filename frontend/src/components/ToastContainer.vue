<template>
  <div class="toast-container" aria-live="polite">
    <div
      v-for="toast in uiStore.toasts"
      :key="toast.id"
      class="toast-item"
      :class="`toast-item--${toast.type}`"
      role="alert"
    >
      <span>{{ toast.message }}</span>
      <button class="toast-close" @click="uiStore.dismissToast(toast.id)" aria-label="Dismiss">&times;</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUIStore } from '../stores/ui'
const uiStore = useUIStore()
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 360px;
}
.toast-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: .85rem;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
  animation: toast-in .2s ease;
}
.toast-item--success { background: #198754; }
.toast-item--danger { background: #dc3545; }
.toast-item--warning { background: #e67e00; }
.toast-item--info { background: #0d6efd; }
.toast-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 1.1rem;
  cursor: pointer;
  opacity: .7;
  padding: 0 2px;
}
.toast-close:hover { opacity: 1; }
@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
