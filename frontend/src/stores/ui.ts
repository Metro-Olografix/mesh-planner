import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ActivityEvent, CoverageJob, JobStatus, Toast, ToastType } from '../types'

export const useUIStore = defineStore('ui', () => {
  const sidebarTab = ref<'nodes' | 'path' | 'activity' | 'jobs'>('nodes')
  const editingNodeId = ref<string | null>(null)
  const showNodeForm = ref(false)
  const activity = ref<ActivityEvent[]>([])
  const jobs = ref<CoverageJob[]>([])
  const toasts = ref<Toast[]>([])
  let toastId = 0

  function pushActivity(event: ActivityEvent) {
    activity.value.unshift(event)
    if (activity.value.length > 50) activity.value.pop()
  }

  function upsertJob(nodeId: string, nodeName: string, status: JobStatus) {
    const existing = jobs.value.find(j => j.nodeId === nodeId)
    if (existing) {
      existing.status = status
      if (status === 'completed' || status === 'failed') {
        existing.finishedAt = new Date()
      }
    } else {
      jobs.value.unshift({
        nodeId,
        nodeName,
        status,
        startedAt: new Date(),
        finishedAt: null,
      })
      // Keep only last 50
      if (jobs.value.length > 50) jobs.value.pop()
    }
  }

  function showToast(message: string, type: ToastType = 'info') {
    const id = ++toastId
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 5000)
  }

  function dismissToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { sidebarTab, editingNodeId, showNodeForm, activity, jobs, toasts, pushActivity, upsertJob, showToast, dismissToast }
})
