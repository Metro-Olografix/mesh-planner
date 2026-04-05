<template>
  <div class="p-3 d-flex flex-column h-100">
    <h6 class="fw-semibold mb-2">Path Planner</h6>

    <div v-if="readOnly" class="alert alert-secondary py-2 small">
      Login to use the path planner.
    </div>

    <template v-if="!readOnly">
    <p v-if="!result" class="text-muted small mb-2">
      Select two nodes as endpoints. The planner finds the best relay path
      through the mesh, maximising the worst-hop SNR (bottleneck).
      SPLAT! terrain data is used where available.
    </p>

    <!-- Node selectors -->
    <div class="mb-2">
      <label class="form-label small mb-1 fw-semibold text-success">Source (A)</label>
      <select v-model="sourceId" class="form-select form-select-sm">
        <option value="">Select node…</option>
        <option
          v-for="n in selectableNodes"
          :key="n.id"
          :value="n.id"
          :disabled="n.id === destId"
        >
          {{ n.name }}
          <template v-if="n.status === 'deployed'"> ✓</template>
          <template v-else> (planned)</template>
        </option>
      </select>
    </div>

    <div class="d-flex justify-content-center my-1">
      <button
        class="btn btn-outline-secondary swap-btn"
        title="Swap source and destination"
        aria-label="Swap source and destination"
        @click="swap"
      >⇅</button>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1 fw-semibold text-danger">Destination (B)</label>
      <select v-model="destId" class="form-select form-select-sm">
        <option value="">Select node…</option>
        <option
          v-for="n in selectableNodes"
          :key="n.id"
          :value="n.id"
          :disabled="n.id === sourceId"
        >
          {{ n.name }}
          <template v-if="n.status === 'deployed'"> ✓</template>
          <template v-else> (planned)</template>
        </option>
      </select>
    </div>

    <!-- Status filters -->
    <div class="mb-2">
      <label class="form-label small mb-1 fw-semibold">Include relay nodes</label>
      <div class="d-flex gap-3">
        <div class="form-check form-check-inline" v-for="s in allStatuses" :key="s">
          <input
            class="form-check-input"
            type="checkbox"
            :id="'status-' + s"
            :value="s"
            v-model="includedStatuses"
          />
          <label class="form-check-label small" :for="'status-' + s">{{ s }}</label>
        </div>
      </div>
    </div>

    <button
      class="btn btn-primary btn-sm mb-2"
      :disabled="!sourceId || !destId || loading"
      @click="findPath"
    >
      <span v-if="loading" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
      {{ loading ? 'Searching…' : 'Find best path' }}
    </button>

    <button
      v-if="result"
      class="btn btn-outline-secondary btn-sm mb-2"
      @click="clearResult"
    >
      Clear result
    </button>

    <!-- Result -->
    <div v-if="result" class="flex-fill overflow-auto">
      <div v-if="pathStale && result.found" class="alert alert-warning py-2 small d-flex align-items-center gap-2">
        <span>Nodes have changed since this path was computed.</span>
        <button class="btn btn-warning btn-sm" style="font-size:.75rem;white-space:nowrap" @click="findPath">Re-run</button>
      </div>
      <div v-if="result.found" class="alert alert-success py-2 small">
        {{ result.message }}
      </div>
      <div v-else class="alert alert-warning py-2 small">
        {{ result.message }}
      </div>

      <div v-if="result.found">
        <div class="fw-semibold small mb-2">Hops ({{ result.hops.length }})</div>
        <div
          v-for="(hop, i) in result.hops"
          :key="i"
          class="d-flex align-items-center gap-2 mb-2"
        >
          <div
            class="hop-badge"
            :style="{
              background: i === 0 ? '#198754' : i === result.hops.length - 1 ? '#dc3545' : '#0d6efd',
            }"
          >
            {{ i === 0 ? 'A' : i === result.hops.length - 1 ? 'B' : `R${i}` }}
          </div>
          <div class="flex-fill" style="font-size:.8rem">
            <div class="fw-semibold">{{ hop.name }}</div>
            <div class="text-muted">{{ formatCoord(hop.lat, uiStore.privacyMode) }}, {{ formatCoord(hop.lon, uiStore.privacyMode) }}</div>
          </div>
          <div v-if="hop.snr_db !== null" class="small text-end" :class="snrClass(hop.snr_db)">
            {{ hop.snr_db }} dB
          </div>
        </div>

        <hr class="my-2" />
        <div class="small text-muted">
          Bottleneck SNR: <strong :class="snrClass(result.bottleneck_snr_db ?? -999)">
            {{ result.bottleneck_snr_db }} dB
          </strong>
        </div>
        <div v-if="result.bottleneck_snr_db !== null && result.bottleneck_snr_db < 10" class="small text-warning mt-1">
          Low bottleneck SNR — consider adding relay nodes.
        </div>
      </div>
    </div>

    <!-- SNR legend (hidden when result is shown to save space on small screens) -->
    <div v-if="!result" class="mt-auto pt-2 border-top small text-muted" style="font-size:.72rem">
      <div class="fw-semibold mb-1">SNR quality</div>
      <div class="d-flex gap-3">
        <span class="text-success">&#9679; &ge;10 dB good</span>
        <span style="color:#e67e00">&#9679; 0–10 dB marginal</span>
        <span class="text-danger">&#9679; &lt;0 dB poor</span>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { NodeStatus, PathResult } from '../types'
import { useNodesStore } from '../stores/nodes'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { formatCoord } from '../utils/privacy'

defineProps<{
  pathStale?: boolean
  readOnly?: boolean
}>()

const emit = defineEmits<{
  pathFound: [result: PathResult | null]
  pickModeChanged: [active: boolean]
}>()

const nodesStore = useNodesStore()
const authStore = useAuthStore()
const uiStore = useUIStore()
const selectableNodes = computed(() => nodesStore.nodes)

const sourceId = ref('')
const destId = ref('')
const result = ref<PathResult | null>(null)
const loading = ref(false)
const pathComputedAt = ref(0)

const allStatuses: NodeStatus[] = ['deployed', 'planned', 'draft']
const includedStatuses = ref<NodeStatus[]>(['deployed', 'planned'])

function swap() {
  const tmp = sourceId.value
  sourceId.value = destId.value
  destId.value = tmp
  result.value = null
}

function clearResult() {
  result.value = null
  sourceId.value = ''
  destId.value = ''
  pathComputedAt.value = 0
  emit('pathFound', null)
}

function snrClass(snr: number): string {
  if (snr >= 10) return 'text-success'
  if (snr >= 0) return 'snr-marginal'
  return 'text-danger'
}

async function findPath() {
  if (!sourceId.value || !destId.value) return
  loading.value = true
  result.value = null
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = authStore.accessToken
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch('/api/path/find', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        source_node_id: sourceId.value,
        destination_node_id: destId.value,
        exclude_statuses: allStatuses.filter(s => !includedStatuses.value.includes(s)),
      }),
    })
    result.value = await res.json()
    pathComputedAt.value = Date.now()
    emit('pathFound', result.value)
  } catch (e) {
    console.error(e)
    uiStore.showToast('Failed to find path. Please try again.', 'danger')
  } finally {
    loading.value = false
  }
}

// No longer uses map clicks — expose stubs so HomeView doesn't break
defineExpose({
  onMapClick: (_lat: number, _lon: number) => {},
  isPicking: () => false,
  pathComputedAt,
})
</script>

<style scoped>
.hop-badge {
  width: 28px; height: 28px; border-radius: 50%;
  color: white; font-size: .75rem; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.snr-marginal { color: #e67e00; }
.swap-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
