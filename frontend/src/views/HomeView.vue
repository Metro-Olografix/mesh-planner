<template>
  <div class="app-layout">
    <!-- Top navbar -->
    <nav class="navbar navbar-dark bg-dark px-3 py-2 d-flex align-items-center" style="height:48px">
      <div class="d-flex align-items-center gap-2">
        <button class="btn btn-outline-secondary btn-sm d-md-none sidebar-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle sidebar">
          ☰
        </button>
        <span class="navbar-brand mb-0 fw-bold" style="font-size:.95rem">
          📡 <span class="d-none d-sm-inline">Metro Olografix —</span> Mesh Planner
        </span>
      </div>
      <div class="ms-auto d-flex align-items-center gap-3">
        <span class="text-secondary small d-none d-sm-inline">{{ username }}</span>
        <button class="btn btn-outline-secondary btn-sm" @click="authStore.logout()">Logout</button>
      </div>
    </nav>

    <!-- Body: sidebar + map -->
    <div class="app-body">
      <!-- Sidebar overlay (mobile) -->
      <div v-if="sidebarOpen" class="sidebar-overlay d-md-none" @click="sidebarOpen = false"></div>
      <!-- Sidebar -->
      <aside class="sidebar border-end bg-white" :class="{ 'sidebar--open': sidebarOpen }">
        <!-- Tab bar -->
        <div class="d-flex border-bottom" style="height:40px" role="tablist" aria-label="Sidebar panels">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            role="tab"
            :aria-selected="activeTab === tab.id"
            :aria-controls="`panel-${tab.id}`"
            class="flex-fill btn btn-sm rounded-0 border-0"
            :class="activeTab === tab.id ? 'bg-light fw-semibold border-bottom border-primary border-2' : 'text-muted'"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Tab content: position:relative + absolute panels prevents overflow into the tab bar -->
        <div class="flex-fill" style="position:relative; overflow:hidden;">
          <div v-show="activeTab === 'nodes'" id="panel-nodes" role="tabpanel" class="tab-panel">
            <NodePanel
              :nodes="nodesStore.nodes"
              :hardware="nodesStore.hardware"
              :loading="nodesStore.loading"
              :selected-id="selectedNodeId"
              :visible-coverage="visibleCoverage"
              :prefill-lat="prefillLat"
              :prefill-lon="prefillLon"
              @select="onNodeSelect"
              @toggle-coverage="toggleCoverage"
              @cancel="ghostPosition = null"
              @saved="ghostPosition = null"
            />
          </div>
          <div v-show="activeTab === 'path'" id="panel-path" role="tabpanel" class="tab-panel">
            <PathPlanner
              ref="pathPlannerRef"
              @path-found="pathResult = $event"
              @pick-mode-changed="pathPickMode = $event"
            />
          </div>
          <div v-show="activeTab === 'activity'" id="panel-activity" role="tabpanel" class="tab-panel">
            <ActivityFeed :activity="uiStore.activity" />
          </div>
          <div v-show="activeTab === 'jobs'" id="panel-jobs" role="tabpanel" class="tab-panel">
            <JobsPanel :jobs="uiStore.jobs" />
          </div>
        </div>
      </aside>

      <!-- Map -->
      <main class="map-area">
        <MapView
          ref="mapViewRef"
          :nodes="nodesStore.nodes"
          :path-result="pathResult"
          :visible-coverage="visibleCoverage"
          :path-pick-mode="pathPickMode"
          :ghost-position="ghostPosition"
          @node-click="selectedNodeId = $event"
          @map-click="onMapClick"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useNodesStore } from '../stores/nodes'
import { useUIStore } from '../stores/ui'
import { getAccessToken } from '../auth'
import MapView from '../components/MapView.vue'
import NodePanel from '../components/NodePanel.vue'
import PathPlanner from '../components/PathPlanner.vue'
import ActivityFeed from '../components/ActivityFeed.vue'
import JobsPanel from '../components/JobsPanel.vue'
import type { PathResult } from '../types'

const authStore = useAuthStore()
const nodesStore = useNodesStore()
const uiStore = useUIStore()

const username = authStore.username
const activeTab = ref<'nodes' | 'path' | 'activity' | 'jobs'>('nodes')
const tabs = [
  { id: 'nodes' as const, label: 'Nodes' },
  { id: 'path' as const, label: 'Path' },
  { id: 'activity' as const, label: 'Activity' },
  { id: 'jobs' as const, label: 'Jobs' },
]

const selectedNodeId = ref<string | null>(null)
const visibleCoverage = ref(new Set<string>())
const pathResult = ref<PathResult | null>(null)
const pathPickMode = ref(false)
const pathPlannerRef = ref<InstanceType<typeof PathPlanner> | null>(null)
const mapViewRef = ref<InstanceType<typeof MapView> | null>(null)
const prefillLat = ref<number | undefined>()
const prefillLon = ref<number | undefined>()
const ghostPosition = ref<{ lat: number; lon: number } | null>(null)
const sidebarOpen = ref(false)

// Sync node coverage_status changes → jobs panel
function nodeJobSnapshots(): Array<{ id: string; name: string; status: string | null }> {
  return nodesStore.nodes.map((n: { id: string; name: string; coverage_status: string | null }) => ({
    id: n.id,
    name: n.name,
    status: n.coverage_status,
  }))
}

watch(
  nodeJobSnapshots,
  (nodes: Array<{ id: string; name: string; status: string | null }>) => {
    for (const n of nodes) {
      if (!n.status || n.status === 'none') continue
      const jobStatus =
        n.status === 'processing' ? 'processing' :
        n.status === 'completed'  ? 'completed'  :
        n.status === 'failed'     ? 'failed'      : 'queued'
      uiStore.upsertJob(n.id, n.name, jobStatus)
    }
  },
  { deep: true },
)

onMounted(async () => {
  await Promise.all([nodesStore.fetchNodes(), nodesStore.fetchHardware()])
  // Load persisted activity history before opening the SSE stream
  try {
    const token = await getAccessToken()
    const res = await fetch('/api/events/recent', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (res.ok) {
      const events: Array<{ type: string; data: { id: string; name: string; by: string }; timestamp: string }> = await res.json()
      // API returns newest-first; iterate in reverse so pushActivity (unshift) keeps newest at top
      for (const e of [...events].reverse()) {
        uiStore.pushActivity({
          type: e.type as any,
          data: e.data,
          timestamp: new Date(e.timestamp),
        })
      }
    }
  } catch {}
  startSSE()
})

// ── SSE ──────────────────────────────────────────────────────────────────────

let evtSource: EventSource | null = null

function startSSE() {
  evtSource = new EventSource('/api/events')
  evtSource.onmessage = (e) => {
    try {
      const { type, data } = JSON.parse(e.data)
      if (type === 'coverage_updated') {
        nodesStore.applyCoverageSSE(data.id, data.status)
      } else {
        nodesStore.applySSEEvent(type, data)
        uiStore.pushActivity({ type, data, timestamp: new Date() })
      }
    } catch {}
  }
}

onUnmounted(() => evtSource?.close())

// ── Interactions ─────────────────────────────────────────────────────────────

function toggleCoverage(id: string) {
  if (visibleCoverage.value.has(id)) {
    visibleCoverage.value.delete(id)
  } else {
    // Exclusive: clear any other active coverage first
    visibleCoverage.value.clear()
    visibleCoverage.value.add(id)
  }
  // force reactivity
  visibleCoverage.value = new Set(visibleCoverage.value)
}

function onNodeSelect(id: string) {
  selectedNodeId.value = id
  mapViewRef.value?.centerOn(id)
}

function onMapClick(lat: number, lon: number) {
  if (activeTab.value === 'path' && pathPlannerRef.value?.isPicking()) {
    pathPlannerRef.value.onMapClick(lat, lon)
  } else if (activeTab.value === 'nodes') {
    // Pre-fill new node position and show ghost marker
    prefillLat.value = lat
    prefillLon.value = lon
    ghostPosition.value = { lat, lon }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}
.sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.map-area {
  flex: 1;
  overflow: hidden;
}
.tab-panel {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}
.sidebar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.4);
  z-index: 999;
}
.sidebar-toggle {
  font-size: 1.1rem;
  padding: 2px 8px;
  line-height: 1;
}

/* Mobile: sidebar slides over the map */
@media (max-width: 767.98px) {
  .sidebar {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 1001;
    transform: translateX(-100%);
    transition: transform .2s ease;
    box-shadow: 2px 0 8px rgba(0,0,0,.15);
    width: 300px;
  }
  .sidebar--open {
    transform: translateX(0);
  }
}
</style>
