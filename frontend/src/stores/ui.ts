import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ActivityEvent, CoverageJob, JobStatus } from '../types'

export const useUIStore = defineStore('ui', () => {
  const sidebarTab = ref<'nodes' | 'path' | 'activity' | 'jobs'>('nodes')
  const editingNodeId = ref<string | null>(null)
  const showNodeForm = ref(false)
  const activity = ref<ActivityEvent[]>([])
  const jobs = ref<CoverageJob[]>([])

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

  return { sidebarTab, editingNodeId, showNodeForm, activity, jobs, pushActivity, upsertJob }
})
