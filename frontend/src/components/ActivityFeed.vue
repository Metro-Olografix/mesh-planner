<template>
  <div class="p-3 d-flex flex-column h-100">
    <h6 class="fw-semibold mb-3">Activity Feed</h6>
    <div v-if="activity.length === 0" class="text-muted small">No recent activity</div>
    <div class="flex-fill overflow-auto">
      <div
        v-for="(ev, i) in activity"
        :key="i"
        class="activity-item py-2 border-bottom"
      >
        <div class="d-flex align-items-center gap-2">
          <span class="activity-icon" :class="iconClass(ev.type)">{{ iconChar(ev.type) }}</span>
          <div style="font-size:.8rem">
            <strong>{{ ev.data.by }}</strong>
            {{ actionText(ev.type) }}
            <em>{{ ev.data.name }}</em>
          </div>
        </div>
        <div class="text-muted ms-4" style="font-size:.72rem">{{ formatTime(ev.timestamp) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ActivityEvent } from '../types'

defineProps<{ activity: ActivityEvent[] }>()

function iconChar(type: ActivityEvent['type']): string {
  return type === 'node_created' ? '+' : type === 'node_updated' ? '✎' : '✕'
}
function iconClass(type: ActivityEvent['type']): string {
  return type === 'node_created' ? 'text-success' : type === 'node_updated' ? 'text-primary' : 'text-danger'
}
function actionText(type: ActivityEvent['type']): string {
  return type === 'node_created' ? ' added ' : type === 'node_updated' ? ' updated ' : ' deleted '
}
function formatTime(d: Date): string {
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) +
    ' ' + d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.activity-item { line-height: 1.4; }
.activity-icon { font-size: .85rem; font-weight: bold; width: 18px; text-align: center; }
</style>
