<template>
  <div class="node-panel d-flex flex-column h-100">
    <!-- Header -->
    <div class="px-3 pt-3 pb-2 border-bottom">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <span class="fw-semibold">Nodes</span>
        <button class="btn btn-primary btn-sm" @click="addNew">+ Add</button>
      </div>
      <input
        v-model="search"
        class="form-control form-control-sm"
        placeholder="Filter nodes…"
      />
    </div>

    <!-- Node form -->
    <div v-if="showForm" class="border-bottom bg-light">
      <NodeForm
        :node="editingNode"
        :hardware="hardware"
        :prefill-lat="prefillLat"
        :prefill-lon="prefillLon"
        @save="onSave"
        @cancel="showForm = false"
      />
    </div>

    <!-- List -->
    <div class="flex-fill overflow-auto">
      <div v-if="loading" class="text-center text-muted py-4">Loading…</div>
      <div v-else-if="filtered.length === 0" class="text-center text-muted py-4">No nodes yet</div>
      <div
        v-for="node in filtered"
        :key="node.id"
        class="node-item px-3 py-2 border-bottom"
        :class="{ 'node-item--active': selectedId === node.id }"
        @click="emit('select', node.id)"
      >
        <div class="d-flex align-items-start justify-content-between">
          <div class="flex-fill me-2" style="min-width:0">
            <div class="d-flex align-items-center gap-2 mb-1">
              <span
                class="badge"
                :class="node.status === 'deployed' ? 'bg-success' : 'bg-warning text-dark'"
                style="font-size:.65rem"
              >
                {{ node.status }}
              </span>
              <span class="fw-semibold text-truncate" style="font-size:.85rem">{{ node.name }}</span>
            </div>
            <div class="text-muted" style="font-size:.75rem">
              {{ node.hardware.manufacturer }} {{ node.hardware.name }}
            </div>
            <div class="text-muted" style="font-size:.72rem">
              {{ node.lat.toFixed(5) }}, {{ node.lon.toFixed(5) }} &nbsp;|&nbsp; {{ node.height_m }}m AGL
            </div>
          </div>

          <!-- Actions -->
          <div class="d-flex flex-column gap-1 ms-1" @click.stop>
            <!-- Coverage toggle -->
            <button
              class="btn btn-xs"
              :class="visibleCoverage.has(node.id) ? 'btn-info' : 'btn-outline-secondary'"
              :title="visibleCoverage.has(node.id) ? 'Hide coverage (Shift+click to invalidate & recompute)' : 'Show coverage (Shift+click to invalidate & recompute)'"
              @click="onCoverageClick(node, $event)"
              style="font-size:.7rem;padding:1px 6px"
            >
              {{ coverageLabel(node) }}
            </button>

            <!-- Recompute button: visible when coverage exists -->
            <button
              v-if="node.coverage_status === 'completed' || node.coverage_status === 'failed'"
              class="btn btn-outline-warning btn-xs"
              title="Recompute coverage"
              style="font-size:.7rem;padding:1px 6px"
              @click="recompute(node)"
            >↺</button>

            <button class="btn btn-outline-secondary btn-xs" style="font-size:.7rem;padding:1px 6px" @click="startEdit(node)">Edit</button>
            <button class="btn btn-outline-danger btn-xs" style="font-size:.7rem;padding:1px 6px" @click="remove(node.id)">Del</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="px-3 py-2 border-top bg-light d-flex gap-3" style="font-size:.75rem">
      <span><span class="dot bg-success"></span> Deployed</span>
      <span><span class="dot bg-warning"></span> Planned</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { HardwareProfile, MeshNode, NodeCreate, NodeUpdate } from '../types'
import NodeForm from './NodeForm.vue'
import { useNodesStore } from '../stores/nodes'

const props = defineProps<{
  nodes: MeshNode[]
  hardware: HardwareProfile[]
  loading: boolean
  selectedId: string | null
  visibleCoverage: Set<string>
  prefillLat?: number
  prefillLon?: number
}>()

const emit = defineEmits<{
  select: [id: string]
  toggleCoverage: [id: string]
}>()

const store = useNodesStore()
const search = ref('')
const showForm = ref(false)
const editingNode = ref<MeshNode | null>(null)

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return props.nodes.filter(n =>
    n.name.toLowerCase().includes(q) ||
    n.hardware.name.toLowerCase().includes(q) ||
    n.status.includes(q)
  )
})

function addNew() {
  editingNode.value = null
  showForm.value = true
}

function startEdit(node: MeshNode) {
  editingNode.value = node
  showForm.value = true
}

async function onSave(payload: NodeCreate | NodeUpdate) {
  if (editingNode.value) {
    await store.updateNode(editingNode.value.id, payload as NodeUpdate)
  } else {
    await store.createNode(payload as NodeCreate)
  }
  showForm.value = false
  editingNode.value = null
}

async function remove(id: string) {
  if (!confirm('Delete this node?')) return
  await store.deleteNode(id)
}

async function onCoverageClick(node: MeshNode, event: MouseEvent) {
  console.log('[coverage] click', node.name, 'status=', node.coverage_status, 'shift=', event.shiftKey, 'visible=', props.visibleCoverage.has(node.id))
  if (event.shiftKey) {
    await recompute(node)
    return
  }
  if (props.visibleCoverage.has(node.id)) {
    console.log('[coverage] toggling off', node.name)
    emit('toggleCoverage', node.id)
    return
  }
  // Auto-trigger computation if not ready
  if (!node.coverage_status || node.coverage_status === 'none' || node.coverage_status === 'invalidated') {
    console.log('[coverage] triggering compute for', node.name)
    try {
      await store.triggerCoverage(node.id)
      console.log('[coverage] compute triggered, starting poll for', node.name)
      pollUntilReady(node.id)
    } catch (err) {
      console.error('[coverage] triggerCoverage failed for', node.name, err)
      alert(`Failed to trigger coverage: ${err}`)
    }
  } else if (node.coverage_status === 'processing') {
    console.log('[coverage] already processing', node.name)
    alert('Coverage is still computing, please wait…')
  } else {
    console.log('[coverage] toggling on', node.name, 'status=', node.coverage_status)
    emit('toggleCoverage', node.id)
  }
}

async function recompute(node: MeshNode) {
  console.log('[coverage] recompute', node.name, 'status=', node.coverage_status)
  if (node.coverage_status === 'processing') {
    alert('Coverage is still computing, please wait…')
    return
  }
  try {
    await store.invalidateAndRecompute(node.id)
    console.log('[coverage] invalidate+recompute triggered for', node.name)
    pollUntilReady(node.id)
  } catch (err) {
    console.error('[coverage] invalidateAndRecompute failed for', node.name, err)
    alert(`Failed to recompute coverage: ${err}`)
  }
}

function pollUntilReady(id: string) {
  let attempts = 0
  const maxAttempts = 60  // 2 min timeout
  console.log('[coverage] starting poll for', id)
  const poll = setInterval(async () => {
    attempts++
    try {
      const status = await store.fetchCoverageStatus(id)
      console.log(`[coverage] poll #${attempts} for ${id}: status=${status}`)
      if (status === 'completed') {
        clearInterval(poll)
        // Only toggle on if not already shown (SSE may have done it first)
        if (!props.visibleCoverage.has(id)) {
          console.log('[coverage] completed, emitting toggleCoverage for', id)
          emit('toggleCoverage', id)
        }
      } else if (status === 'failed') {
        clearInterval(poll)
        console.error('[coverage] computation failed for', id)
        alert('Coverage computation failed for this node')
      } else if (attempts >= maxAttempts) {
        clearInterval(poll)
        console.error('[coverage] poll timeout for', id)
        alert('Coverage computation timed out')
      }
    } catch (err) {
      console.error('[coverage] poll error for', id, err)
      clearInterval(poll)
    }
  }, 2000)
}

function coverageLabel(node: MeshNode): string {
  if (props.visibleCoverage.has(node.id)) return '◉'
  if (node.coverage_status === 'processing') return '⏳'
  if (node.coverage_status === 'completed') return '◎'
  return '○'
}
</script>

<style scoped>
.node-item { cursor: pointer; transition: background .1s; }
.node-item:hover { background: #f8f9fa; }
.node-item--active { background: #e7f3ff; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
.btn-xs { line-height:1.2; }
</style>
