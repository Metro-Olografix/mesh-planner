<template>
  <div class="node-panel d-flex flex-column h-100">
    <!-- Header -->
    <div class="px-3 pt-3 pb-2 border-bottom">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <span class="fw-semibold">Nodes</span>
        <button v-if="!readOnly" class="btn btn-primary btn-sm" @click="addNew">+ Add</button>
        <span v-else class="badge bg-secondary" style="font-size:.7rem">read-only</span>
      </div>
      <input
        v-model="search"
        class="form-control form-control-sm mb-1"
        placeholder="Filter nodes…"
      />
      <div class="d-flex gap-1" role="group" aria-label="Filter by status">
        <button
          v-for="f in statusFilters"
          :key="f.value"
          class="btn btn-filter flex-fill"
          :class="activeFilter === f.value ? f.activeClass : 'btn-outline-secondary'"
          :style="statusCounts[f.value] === 0 ? 'opacity:.4' : ''"
          @click="activeFilter = activeFilter === f.value ? null : f.value"
        >{{ f.label }} <span class="filter-count">{{ statusCounts[f.value] }}</span></button>
      </div>
    </div>

    <!-- Node form (write-mode only) -->
    <div v-if="showForm && !readOnly" class="border-bottom bg-light">
      <NodeForm
        :node="editingNode"
        :hardware="hardware"
        :prefill-lat="prefillLat"
        :prefill-lon="prefillLon"
        @save="onSave"
        @cancel="onCancel"
      />
    </div>

    <!-- List -->
    <div class="flex-fill overflow-auto">
      <div v-if="loading" class="text-center text-muted py-4">Loading…</div>
      <div v-else-if="filtered.length === 0 && props.nodes.length === 0" class="text-center text-muted py-4">No nodes yet</div>
      <div v-else-if="filtered.length === 0" class="text-center text-muted py-4">
        No nodes match the filter.
        <br>
        <button class="btn btn-link btn-sm p-0 mt-1" style="font-size:.8rem" @click="search = ''; activeFilter = null">Clear filters</button>
      </div>
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
                :class="node.status === 'deployed' ? 'bg-success' : node.status === 'planned' ? 'badge--planned' : 'bg-secondary'"
                style="font-size:.65rem"
              >
                {{ node.status === 'deployed' ? '✓ deployed' : node.status === 'planned' ? '◆ planned' : '● draft' }}
              </span>
              <span class="fw-semibold text-truncate" style="font-size:.85rem">{{ node.name }}</span>
            </div>
            <div class="text-muted" style="font-size:.75rem">
              {{ node.hardware.manufacturer }} {{ node.hardware.name }}
            </div>
            <div class="text-muted" style="font-size:.72rem">
              {{ formatCoord(node.lat, uiStore.privacyMode) }}, {{ formatCoord(node.lon, uiStore.privacyMode) }} &nbsp;|&nbsp; {{ node.height_m }}m AGL
            </div>
          </div>

          <!-- Actions -->
          <div class="node-actions" @click.stop>
            <button
              v-if="!readOnly"
              class="action-btn coverage-btn"
              :class="{ 'coverage-btn--active': visibleCoverage.has(node.id) }"
              :title="visibleCoverage.has(node.id) ? 'Hide coverage' : 'Show coverage'"
              :aria-label="coverageAriaLabel(node)"
              @click="onCoverageClick(node, $event)"
            >
              {{ coverageLabel(node) }}
            </button>

            <div v-if="!readOnly" class="menu-wrap">
              <button
                class="action-btn menu-trigger"
                aria-label="More actions"
                @click="openMenu = openMenu === node.id ? null : node.id"
              >⋮</button>
              <Transition name="menu-fade">
                <div v-if="openMenu === node.id" v-click-outside="() => openMenu = null" class="action-menu">
                  <button class="action-menu-item" @click="startEdit(node); openMenu = null">Edit</button>
                  <button
                    v-if="node.coverage_status === 'completed' || node.coverage_status === 'failed'"
                    class="action-menu-item"
                    @click="recompute(node); openMenu = null"
                  >Recompute coverage</button>
                  <div v-if="confirmDeleteId === node.id" class="action-menu-item action-menu-item--danger d-flex align-items-center gap-2">
                    <span style="font-size:.78rem">Delete?</span>
                    <button class="btn btn-danger btn-sm" style="font-size:.7rem;padding:1px 8px" @click="confirmDelete(node.id)">Yes</button>
                    <button class="btn btn-outline-secondary btn-sm" style="font-size:.7rem;padding:1px 8px" @click="confirmDeleteId = null">No</button>
                  </div>
                  <button v-else class="action-menu-item action-menu-item--danger" @click="promptDelete(node.id)">Delete</button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend (write-mode only — coverage controls are hidden in read-only) -->
    <div v-if="!readOnly" class="px-3 py-2 border-top bg-light" style="font-size:.75rem">
      <div class="d-flex gap-3 text-muted" style="font-size:.7rem">
        <span>◉ Visible</span>
        <span>◎ Computed</span>
        <span>○ Not computed</span>
        <span>⏳ Computing</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, type Directive } from 'vue'
import type { HardwareProfile, MeshNode, NodeCreate, NodeUpdate } from '../types'
import NodeForm from './NodeForm.vue'
import { useNodesStore } from '../stores/nodes'
import { useUIStore } from '../stores/ui'
import { formatCoord } from '../utils/privacy'

// Click-outside directive for closing the dropdown
const vClickOutside: Directive = {
  mounted(el, binding) {
    (el as any).__clickOutside = (e: Event) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    setTimeout(() => document.addEventListener('click', (el as any).__clickOutside), 0)
  },
  unmounted(el) {
    document.removeEventListener('click', (el as any).__clickOutside)
  },
}

const props = defineProps<{
  nodes: MeshNode[]
  hardware: HardwareProfile[]
  loading: boolean
  selectedId: string | null
  visibleCoverage: Set<string>
  prefillLat?: number
  prefillLon?: number
  readOnly?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  toggleCoverage: [id: string]
  cancel: []
  saved: []
}>()

const store = useNodesStore()
const uiStore = useUIStore()
const search = ref('')
const showForm = ref(false)
const editingNode = ref<MeshNode | null>(null)
const activeFilter = ref<string | null>(null)
const openMenu = ref<string | null>(null)
const confirmDeleteId = ref<string | null>(null)
let confirmTimeout: ReturnType<typeof setTimeout> | null = null

const statusFilters = [
  { value: 'planned',  label: 'Planned',  activeClass: 'btn-warning' },
  { value: 'deployed', label: 'Deployed', activeClass: 'btn-success' },
  { value: 'draft',    label: 'Draft',    activeClass: 'btn-secondary' },
] as const

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  return props.nodes.filter(n => {
    if (activeFilter.value && n.status !== activeFilter.value) return false
    return !q || n.name.toLowerCase().includes(q) || n.hardware.name.toLowerCase().includes(q)
  })
})

const statusCounts = computed(() => {
  const q = search.value.toLowerCase()
  const matchesSearch = (n: (typeof props.nodes)[0]) =>
    !q || n.name.toLowerCase().includes(q) || n.hardware.name.toLowerCase().includes(q)
  return {
    planned:  props.nodes.filter(n => n.status === 'planned'  && matchesSearch(n)).length,
    deployed: props.nodes.filter(n => n.status === 'deployed' && matchesSearch(n)).length,
    draft:    props.nodes.filter(n => n.status === 'draft'    && matchesSearch(n)).length,
  }
})

function addNew() {
  editingNode.value = null
  showForm.value = true
}

function onCancel() {
  const wasNew = !editingNode.value
  showForm.value = false
  editingNode.value = null
  if (wasNew) emit('cancel')
}

function startEdit(node: MeshNode) {
  editingNode.value = node
  showForm.value = true
}

async function onSave(payload: NodeCreate | NodeUpdate) {
  const wasNew = !editingNode.value
  if (editingNode.value) {
    await store.updateNode(editingNode.value.id, payload as NodeUpdate)
  } else {
    await store.createNode(payload as NodeCreate)
  }
  showForm.value = false
  editingNode.value = null
  if (wasNew) emit('saved')
}

function promptDelete(id: string) {
  confirmDeleteId.value = id
  if (confirmTimeout) clearTimeout(confirmTimeout)
  confirmTimeout = setTimeout(() => { confirmDeleteId.value = null }, 5000)
}

async function confirmDelete(id: string) {
  confirmDeleteId.value = null
  if (confirmTimeout) clearTimeout(confirmTimeout)
  openMenu.value = null
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
      uiStore.showToast(`Failed to trigger coverage: ${err}`, 'danger')
    }
  } else if (node.coverage_status === 'processing') {
    console.log('[coverage] already processing', node.name)
    uiStore.showToast('Coverage is still computing, please wait…', 'info')
  } else {
    console.log('[coverage] toggling on', node.name, 'status=', node.coverage_status)
    emit('toggleCoverage', node.id)
  }
}

async function recompute(node: MeshNode) {
  console.log('[coverage] recompute', node.name, 'status=', node.coverage_status)
  if (node.coverage_status === 'processing') {
    uiStore.showToast('Coverage is still computing, please wait…', 'info')
    return
  }
  try {
    await store.invalidateAndRecompute(node.id)
    console.log('[coverage] invalidate+recompute triggered for', node.name)
    pollUntilReady(node.id)
  } catch (err) {
    console.error('[coverage] invalidateAndRecompute failed for', node.name, err)
    uiStore.showToast(`Failed to recompute coverage: ${err}`, 'danger')
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
        uiStore.showToast('Coverage computation failed for this node', 'danger')
      } else if (attempts >= maxAttempts) {
        clearInterval(poll)
        console.error('[coverage] poll timeout for', id)
        uiStore.showToast('Coverage computation timed out', 'warning')
      }
    } catch (err) {
      console.error('[coverage] poll error for', id, err)
      clearInterval(poll)
    }
  }, 2000)
}

function coverageLabel(node: MeshNode): string {
  if (props.visibleCoverage.has(node.id)) return '◉ On'
  if (node.coverage_status === 'processing') return '⏳'
  if (node.coverage_status === 'completed') return '◎'
  return '○'
}

function coverageAriaLabel(node: MeshNode): string {
  if (props.visibleCoverage.has(node.id)) return `Hide coverage for ${node.name}`
  if (node.coverage_status === 'processing') return `Coverage computing for ${node.name}`
  if (node.coverage_status === 'completed') return `Show coverage for ${node.name}`
  return `Compute and show coverage for ${node.name}`
}
</script>

<style scoped>
.node-item { cursor: pointer; transition: background .15s; }
.node-item:hover { background: #f8f9fa; }
.node-item--active { background: #e7f3ff; }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }
.dot--planned { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; background:#e67e00; }
.btn-filter { font-size:.7rem; padding:2px 7px; }
.filter-count { font-size:.65rem; opacity:.75; }
.badge--planned { background-color:#e67e00; color:#fff; }

/* ── Node actions ─────────────────────────────────────────── */
.node-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  background: #fff;
  color: #495057;
  font-size: .72rem;
  padding: 3px 8px;
  min-height: 28px;
  cursor: pointer;
  transition: all .15s;
}
.action-btn:hover {
  background: #f0f0f0;
  border-color: #adb5bd;
}
.coverage-btn--active {
  background: #0dcaf0;
  border-color: #0dcaf0;
  color: #fff;
}
.coverage-btn--active:hover {
  background: #31d2f2;
  border-color: #31d2f2;
}
.menu-wrap {
  position: relative;
}
.menu-trigger {
  font-weight: bold;
  letter-spacing: 1px;
  padding: 3px 6px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: .9rem;
}
.menu-trigger:hover {
  background: #f3f4f6;
  color: #374151;
  border: none;
}
.action-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 50;
  min-width: 160px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,.12);
  padding: 4px 0;
  display: flex;
  flex-direction: column;
}
.action-menu-item {
  background: none;
  border: none;
  text-align: left;
  padding: 7px 14px;
  font-size: .8rem;
  color: #374151;
  cursor: pointer;
  transition: background .1s;
}
.action-menu-item:hover {
  background: #f3f4f6;
}
.action-menu-item--danger {
  color: #dc3545;
}
.action-menu-item--danger:hover {
  background: #fef2f2;
}

/* Dropdown transition */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity .12s ease, transform .12s ease;
}
.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
