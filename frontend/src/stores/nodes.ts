import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { HardwareProfile, MeshNode, NodeCreate, NodeUpdate } from '../types'
import { useAuthStore } from './auth'

const BASE = '/api'

async function authFetch(url: string, opts: RequestInit = {}, token: string | null) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> ?? {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(url, { ...opts, headers })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res
}

export const useNodesStore = defineStore('nodes', () => {
  const nodes = ref<MeshNode[]>([])
  const hardware = ref<HardwareProfile[]>([])
  const loading = ref(false)

  function token() {
    return useAuthStore().accessToken
  }

  async function fetchNodes() {
    loading.value = true
    try {
      const res = await authFetch(`${BASE}/nodes/`, {}, token())
      nodes.value = await res.json()
    } finally {
      loading.value = false
    }
  }

  async function fetchHardware() {
    const res = await authFetch(`${BASE}/hardware/`, {}, token())
    hardware.value = await res.json()
  }

  async function createNode(payload: NodeCreate): Promise<MeshNode> {
    const res = await authFetch(`${BASE}/nodes/`, { method: 'POST', body: JSON.stringify(payload) }, token())
    const node: MeshNode = await res.json()
    nodes.value.unshift(node)
    return node
  }

  async function updateNode(id: string, payload: NodeUpdate): Promise<MeshNode> {
    const res = await authFetch(`${BASE}/nodes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }, token())
    const updated: MeshNode = await res.json()
    const idx = nodes.value.findIndex(n => n.id === id)
    if (idx !== -1) nodes.value[idx] = updated
    return updated
  }

  async function deleteNode(id: string) {
    await authFetch(`${BASE}/nodes/${id}`, { method: 'DELETE' }, token())
    nodes.value = nodes.value.filter(n => n.id !== id)
  }

  async function triggerCoverage(id: string) {
    await authFetch(`${BASE}/coverage/${id}/compute`, { method: 'POST' }, token())
    // Optimistically update coverage_status
    const node = nodes.value.find(n => n.id === id)
    if (node) node.coverage_status = 'processing'
  }

  async function invalidateAndRecompute(id: string) {
    await authFetch(`${BASE}/coverage/${id}/invalidate_and_recompute`, { method: 'POST' }, token())
    const node = nodes.value.find(n => n.id === id)
    if (node) node.coverage_status = 'processing'
  }

  async function recomputeAll(): Promise<{ nodes_queued: number }> {
    const res = await authFetch(`${BASE}/coverage/recompute_all`, { method: 'POST' }, token())
    const data = await res.json()
    // Optimistically mark all nodes as processing
    for (const node of nodes.value) {
      node.coverage_status = 'processing'
    }
    return data
  }

  async function fetchCoverageStatus(id: string): Promise<string> {
    const res = await authFetch(`${BASE}/coverage/${id}/status`, {}, token())
    const data = await res.json()
    const node = nodes.value.find(n => n.id === id)
    if (node) node.coverage_status = data.invalidated ? 'invalidated' : data.status
    return data.status
  }

  // Called when coverage_updated SSE event arrives
  function applyCoverageSSE(id: string, status: string) {
    const node = nodes.value.find(n => n.id === id)
    if (node) node.coverage_status = status
  }

  // Called by SSE handler to sync remote changes
  function applySSEEvent(type: string, data: { id: string }) {
    if (type === 'node_deleted') {
      nodes.value = nodes.value.filter(n => n.id !== data.id)
    } else if (type === 'node_created' || type === 'node_updated') {
      // Re-fetch the specific node
      authFetch(`${BASE}/nodes/${data.id}`, {}, token())
        .then(r => r.json())
        .then((n: MeshNode) => {
          const idx = nodes.value.findIndex(x => x.id === n.id)
          if (idx !== -1) nodes.value[idx] = n
          else nodes.value.unshift(n)
        })
        .catch(() => {})
    }
  }

  return { nodes, hardware, loading, fetchNodes, fetchHardware, createNode, updateNode, deleteNode, triggerCoverage, invalidateAndRecompute, recomputeAll, fetchCoverageStatus, applySSEEvent, applyCoverageSSE }
})
