<template>
  <div class="app-layout">
    <!-- Top navbar -->
    <nav class="navbar navbar-dark bg-dark px-3">
      <div class="navbar-left">
        <button class="nav-btn d-md-none" @click="sidebarOpen = !sidebarOpen" :aria-label="$t('nav.toggle_sidebar')">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path fill-rule="evenodd" d="M2.5 12a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5"/>
          </svg>
        </button>
        <span class="navbar-brand mb-0 fw-bold d-flex align-items-center gap-2">
          <img v-if="hasCustomLogo()" :src="'/api/custom/logo'" alt="Logo" style="height:24px;width:auto;object-fit:contain" />
          <span v-else aria-hidden="true">📡</span>
          <span class="brand-full d-none d-sm-inline text-white-50">Metro Olografix —</span><span>Mesh Planner</span>
        </span>
      </div>
      <div class="navbar-right">
        <!-- Group 1: tertiary links — desktop only -->
        <a
          href="/try"
          class="nav-btn nav-btn--text d-none d-md-inline-flex"
          :title="$t('try.page_title')"
        >{{ $t('try.page_title') }}</a>
        <a
          href="https://github.com/Metro-Olografix/mesh-planner"
          target="_blank"
          rel="noopener noreferrer"
          class="nav-btn d-none d-md-inline-flex"
          :title="$t('nav.source_code')"
          :aria-label="$t('nav.source_code')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
          </svg>
        </a>
        <span class="nav-divider d-none d-md-block"></span>

        <!-- Group 2: utility controls -->
        <button
          class="nav-btn"
          :class="uiStore.privacyMode ? 'nav-btn--active' : ''"
          :disabled="uiStore.privacyLocked"
          :title="uiStore.privacyLocked ? $t('nav.privacy_locked_tooltip') : uiStore.privacyMode ? $t('nav.privacy_on_tooltip') : $t('nav.privacy_off_tooltip')"
          @click="uiStore.togglePrivacy()"
        >
          <svg v-if="uiStore.privacyMode" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2"/>
          </svg>
        </button>
        <!-- Language switcher: always visible on desktop, in overflow on mobile -->
        <button class="nav-btn nav-btn--text d-none d-md-inline-flex" @click="toggleLanguage()" :title="$t('nav.language')">
          {{ locale.toUpperCase() }}
        </button>
        <span class="nav-divider d-none d-md-block"></span>

        <!-- Group 3: user identity + primary action -->
        <span class="nav-username d-none d-md-inline">{{ displayName }}</span>
        <button v-if="authStore.isAuthenticated" class="nav-btn nav-btn--text" @click="authStore.logout()">{{ $t('nav.logout') }}</button>
        <button v-else class="nav-btn nav-btn--text nav-btn--primary" @click="handleLogin()">{{ $t('nav.login') }}</button>

        <!-- Mobile: overflow menu trigger -->
        <button
          class="nav-btn d-md-none"
          @click.stop="mobileMenuOpen = !mobileMenuOpen"
          :aria-expanded="mobileMenuOpen"
          :aria-label="$t('nav.more')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M9.5 13a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0m0-5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0m0-5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/>
          </svg>
        </button>
      </div>

      <!-- Mobile overflow: backdrop + dropdown -->
      <div v-if="mobileMenuOpen" class="nav-overflow-backdrop d-md-none" @click="mobileMenuOpen = false"></div>
      <div v-if="mobileMenuOpen" class="nav-overflow-menu d-md-none" @click.stop>
        <div v-if="authStore.isAuthenticated" class="nav-overflow-user">{{ displayName }}</div>
        <div v-if="authStore.isAuthenticated" class="nav-overflow-sep"></div>
        <button class="nav-overflow-item" @click="toggleLanguage(); mobileMenuOpen = false">
          {{ locale === 'en' ? '🇮🇹 Italiano' : '🇬🇧 English' }}
        </button>
        <div class="nav-overflow-sep"></div>
        <a href="/try" class="nav-overflow-item" @click="mobileMenuOpen = false">{{ $t('try.page_title') }}</a>
        <a
          href="https://github.com/Metro-Olografix/mesh-planner"
          target="_blank"
          rel="noopener noreferrer"
          class="nav-overflow-item"
          @click="mobileMenuOpen = false"
        >GitHub</a>
      </div>
    </nav>

    <!-- Body: sidebar + map -->
    <div class="app-body">
      <!-- Sidebar overlay (mobile) -->
      <div v-if="sidebarOpen" class="sidebar-overlay d-md-none" @click="sidebarOpen = false"></div>
      <!-- Sidebar -->
      <aside class="sidebar border-end bg-white" :class="{ 'sidebar--open': sidebarOpen }">
        <!-- Tab bar -->
        <div class="d-flex border-bottom" style="height:40px" role="tablist" :aria-label="$t('nav.toggle_sidebar')">
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
              :read-only="authStore.isReadOnly"
              @select="onNodeSelect"
              @toggle-coverage="toggleCoverage"
              @cancel="ghostPosition = null"
              @saved="ghostPosition = null"
            />
          </div>
          <div v-show="activeTab === 'path'" id="panel-path" role="tabpanel" class="tab-panel">
            <PathPlanner
              ref="pathPlannerRef"
              :path-stale="pathStale"
              :read-only="authStore.isReadOnly"
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
          @login-request="onLoginRequest"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useNodesStore } from '../stores/nodes'
import { useUIStore } from '../stores/ui'
import { getAccessToken, login, hasCustomLogo } from '../auth'
import { setLanguage } from '../i18n'
import MapView from '../components/MapView.vue'
import NodePanel from '../components/NodePanel.vue'
import PathPlanner from '../components/PathPlanner.vue'
import ActivityFeed from '../components/ActivityFeed.vue'
import JobsPanel from '../components/JobsPanel.vue'
import type { PathResult } from '../types'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const nodesStore = useNodesStore()
const uiStore = useUIStore()

const displayName = computed(() =>
  authStore.isReadOnly ? t('auth.guest') : authStore.username
)

async function handleLogin() {
  await login()
}

function toggleLanguage() {
  const next = locale.value === 'en' ? 'it' : 'en'
  setLanguage(next)
}

const mobileMenuOpen = ref(false)
const activeTab = ref<'nodes' | 'path' | 'activity' | 'jobs'>('nodes')
const tabs = computed(() => {
  const all = [
    { id: 'nodes' as const, label: t('tabs.nodes') },
    { id: 'path' as const, label: t('tabs.path') },
    { id: 'activity' as const, label: t('tabs.activity') },
    { id: 'jobs' as const, label: t('tabs.jobs') },
  ]
  return authStore.isAuthenticated ? all : all.filter(tab => tab.id !== 'jobs')
})

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
const lastNodeMutationAt = ref(0)
const pathStale = computed(() => {
  const computedAt = pathPlannerRef.value?.pathComputedAt ?? 0
  return computedAt > 0 && lastNodeMutationAt.value > computedAt
})

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

// Force privacy mode on for unauthenticated users in public-access mode
watch(
  () => authStore.isReadOnly,
  (readOnly) => {
    if (readOnly) {
      uiStore.privacyLocked = true
      uiStore.privacyMode = true
    } else {
      uiStore.privacyLocked = false
    }
  },
  { immediate: true },
)

onMounted(async () => {
  await Promise.all([nodesStore.fetchNodes(), nodesStore.fetchHardware()])
  // Restore position the user picked before the login redirect
  const raw = sessionStorage.getItem(PENDING_POSITION_KEY)
  if (raw && authStore.isAuthenticated) {
    try {
      const { lat, lon } = JSON.parse(raw)
      prefillLat.value = lat
      prefillLon.value = lon
      ghostPosition.value = { lat, lon }
      activeTab.value = 'nodes'
    } catch {}
    sessionStorage.removeItem(PENDING_POSITION_KEY)
  }
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

async function startSSE() {
  const token = await getAccessToken()
  const url = token ? `/api/events?token=${encodeURIComponent(token)}` : '/api/events'
  evtSource = new EventSource(url)
  evtSource.onmessage = (e) => {
    try {
      const { type, data } = JSON.parse(e.data)
      if (type === 'coverage_updated') {
        nodesStore.applyCoverageSSE(data.id, data.status)
      } else {
        nodesStore.applySSEEvent(type, data)
        uiStore.pushActivity({ type, data, timestamp: new Date() })
        lastNodeMutationAt.value = Date.now()
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

const PENDING_POSITION_KEY = 'meshplanner_pending_position'

function onMapClick(lat: number, lon: number) {
  if (!authStore.isAuthenticated) {
    // Show ghost marker with login prompt — position is preserved across login redirect
    ghostPosition.value = { lat, lon }
    return
  }
  if (activeTab.value === 'path' && pathPlannerRef.value?.isPicking()) {
    pathPlannerRef.value.onMapClick(lat, lon)
  } else if (activeTab.value === 'nodes') {
    // Pre-fill new node position and show ghost marker
    prefillLat.value = lat
    prefillLon.value = lon
    ghostPosition.value = { lat, lon }
  }
}

function onLoginRequest() {
  const pos = ghostPosition.value
  if (pos) {
    sessionStorage.setItem(PENDING_POSITION_KEY, JSON.stringify(pos))
  }
  handleLogin()
}
</script>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────────────────── */
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

/* ── Navbar ──────────────────────────────────────────────────────────────── */
.navbar {
  height: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;        /* never wrap onto a second line */
  overflow: hidden;
}
.navbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;             /* allow text to shrink/truncate before pushing right side off */
  flex: 1;
  overflow: hidden;
}
.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;           /* right side never shrinks — it's always fully visible */
}
.navbar-brand {
  font-size: .9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.nav-username {
  font-size: .8rem;
  color: rgba(255,255,255,.45);
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Unified icon/text button for the navbar — all the same 32×32 tap target */
.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  min-width: 32px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,.2);
  background: transparent;
  color: rgba(255,255,255,.75);
  font-size: .8125rem;
  line-height: 1;
  cursor: pointer;
  text-decoration: none;
  transition: background .15s, border-color .15s, color .15s;
  white-space: nowrap;
}
.nav-btn:hover:not(:disabled) {
  background: rgba(255,255,255,.1);
  border-color: rgba(255,255,255,.4);
  color: #fff;
}
.nav-btn:disabled {
  opacity: .45;
  cursor: not-allowed;
}
.nav-btn--active {
  background: #ffc107;
  border-color: #ffc107;
  color: #000;
}
.nav-btn--active:hover:not(:disabled) {
  background: #ffca2c;
  border-color: #ffca2c;
  color: #000;
}
.nav-btn--text {
  padding: 0 12px;
}
.nav-btn--primary {
  border-color: rgba(255,255,255,.5);
  color: #fff;
}
.nav-btn--primary:hover:not(:disabled) {
  background: rgba(255,255,255,.15);
  border-color: #fff;
}

/* ── Navbar divider ──────────────────────────────────────────────────────── */
.nav-divider {
  width: 1px;
  height: 20px;
  background: rgba(255,255,255,.15);
  flex-shrink: 0;
}

/* ── Mobile overflow menu ────────────────────────────────────────────────── */
.nav-overflow-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1099;
}
.nav-overflow-menu {
  position: fixed;
  top: 48px;
  right: 8px;
  z-index: 1100;
  background: #2b2f33;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 8px;
  padding: 4px 0;
  min-width: 200px;
  box-shadow: 0 8px 24px rgba(0,0,0,.4);
}
.nav-overflow-user {
  padding: 10px 16px 8px;
  font-size: .8rem;
  font-weight: 600;
  color: rgba(255,255,255,.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-overflow-sep {
  height: 1px;
  background: rgba(255,255,255,.1);
  margin: 4px 0;
}
.nav-overflow-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: rgba(255,255,255,.75);
  font-size: .85rem;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  transition: background .12s, color .12s;
}
.nav-overflow-item:hover {
  background: rgba(255,255,255,.08);
  color: #fff;
}

/* ── Sidebar overlay ─────────────────────────────────────────────────────── */
.sidebar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.4);
  z-index: 999;
}

/* ── Mobile: sidebar slides over the map ────────────────────────────────── */
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
