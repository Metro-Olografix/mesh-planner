<template>
  <div class="p-3 d-flex flex-column h-100">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">{{ $t('jobs.title') }}</h6>
      <template v-if="authStore.isAuthenticated">
        <div v-if="confirmRecompute" class="d-flex align-items-center gap-2">
          <span class="small text-warning">{{ $t('jobs.recompute_all_confirm') }}</span>
          <button class="btn btn-warning btn-sm" style="font-size:.75rem" @click="doRecomputeAll">{{ $t('common.yes') }}</button>
          <button class="btn btn-outline-secondary btn-sm" style="font-size:.75rem" @click="confirmRecompute = false">{{ $t('common.no') }}</button>
        </div>
        <button
          v-else
          class="btn btn-warning btn-sm"
          :disabled="recomputingAll"
          @click="promptRecomputeAll"
          :title="$t('node.actions.recompute_coverage')"
        >
          {{ recomputingAll ? $t('common.queuing') : '↺ ' + $t('common.recompute_all') }}
        </button>
      </template>
    </div>

    <div v-if="jobs.length === 0" class="text-muted small text-center py-4">
      <div style="font-size:1.5rem;margin-bottom:4px">--</div>
      {{ $t('jobs.no_jobs') }}<br/>
      <span style="font-size:.72rem">{{ $t('jobs.empty_help') }}</span>
    </div>

    <div class="flex-fill overflow-auto">
      <div
        v-for="job in jobs"
        :key="job.nodeId"
        class="job-item d-flex align-items-center gap-2 py-2 border-bottom"
      >
        <!-- Status indicator -->
        <span class="job-icon" :class="iconClass(job.status)">{{ iconChar(job.status) }}</span>

        <div class="flex-fill" style="min-width:0; font-size:.82rem">
          <div class="fw-semibold text-truncate">{{ job.nodeName }}</div>
          <div class="text-muted" style="font-size:.72rem">
            {{ $t('jobs.started') }} {{ formatTime(job.startedAt) }}
            <template v-if="job.finishedAt">
              · {{ $t('jobs.done') }} {{ formatTime(job.finishedAt) }}
            </template>
          </div>
        </div>

        <!-- Progress bar for processing jobs -->
        <div v-if="job.status === 'processing' || job.status === 'queued'" style="width:60px">
          <div class="progress" style="height:6px">
            <div
              class="progress-bar progress-bar-striped progress-bar-animated"
              :class="job.status === 'queued' ? 'bg-secondary' : 'bg-primary'"
              style="width:100%"
            ></div>
          </div>
          <div class="text-muted text-center" style="font-size:.65rem">{{ $t('jobs.' + job.status) }}</div>
        </div>

        <span v-else class="badge" :class="badgeClass(job.status)" style="font-size:.65rem">
          {{ $t('common.' + job.status) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CoverageJob, JobStatus } from '../types'
import { useNodesStore } from '../stores/nodes'
import { useUIStore } from '../stores/ui'
import { useAuthStore } from '../stores/auth'

defineProps<{ jobs: CoverageJob[] }>()

const { t, locale } = useI18n()
const nodesStore = useNodesStore()
const uiStore = useUIStore()
const authStore = useAuthStore()
const recomputingAll = ref(false)
const confirmRecompute = ref(false)
let confirmTimeout: ReturnType<typeof setTimeout> | null = null

function promptRecomputeAll() {
  confirmRecompute.value = true
  if (confirmTimeout) clearTimeout(confirmTimeout)
  confirmTimeout = setTimeout(() => { confirmRecompute.value = false }, 5000)
}

async function doRecomputeAll() {
  confirmRecompute.value = false
  if (confirmTimeout) clearTimeout(confirmTimeout)
  recomputingAll.value = true
  try {
    const result = await nodesStore.recomputeAll()
    uiStore.showToast(t('jobs.recompute_all_success', { count: result.nodes_queued }), 'success')
  } catch (err) {
    uiStore.showToast(t('jobs.recompute_all_failed', { err }), 'danger')
  } finally {
    recomputingAll.value = false
  }
}

function iconChar(status: JobStatus): string {
  if (status === 'queued') return '…'
  if (status === 'processing') return '⚙'
  if (status === 'completed') return '✓'
  return '✕'
}

function iconClass(status: JobStatus): string {
  if (status === 'queued') return 'text-secondary'
  if (status === 'processing') return 'text-primary'
  if (status === 'completed') return 'text-success'
  return 'text-danger'
}

function badgeClass(status: JobStatus): string {
  if (status === 'completed') return 'bg-success'
  if (status === 'failed') return 'bg-danger'
  return 'bg-secondary'
}

function formatTime(d: Date): string {
  return d.toLocaleDateString(locale.value, { day: '2-digit', month: '2-digit' }) +
    ' ' + d.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.job-item { line-height: 1.4; }
.job-icon { font-size: .9rem; font-weight: bold; width: 18px; text-align: center; flex-shrink: 0; }
</style>
