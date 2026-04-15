<template>
  <div style="position:relative;height:100%;width:100%">
    <div id="map" ref="mapEl"></div>
    <div v-if="isLoadingCoverage" class="coverage-loading-badge">
      <span class="spinner-border spinner-border-sm me-1" role="status"></span>
      {{ $t('map.loading_coverage') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import GeoRasterLayer from 'georaster-layer-for-leaflet'
import parseGeoraster from 'georaster'
import type { MeshNode, PathResult } from '../types'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { fuzzCoords, formatCoord } from '../utils/privacy'

// We use custom divIcons for all markers so no default icon fix is needed

const props = defineProps<{
  nodes: MeshNode[]
  pathResult: PathResult | null
  visibleCoverage: Set<string>   // node ids whose coverage overlay is shown
  pathPickMode: boolean
  ghostPosition?: { lat: number; lon: number } | null
}>()

const emit = defineEmits<{
  nodeClick: [id: string]
  mapClick: [lat: number, lon: number]
  loginRequest: []
}>()

const authStore = useAuthStore()
const uiStore = useUIStore()
const { t } = useI18n()
const mapEl = ref<HTMLElement>()
let map: L.Map
let markersLayer: L.LayerGroup
let pathLayer: L.LayerGroup
const rasterLayers = new Map<string, any>()     // id → active Leaflet layer on map
const loadingIds = ref(new Set<string>())        // ids currently being fetched
const isLoadingCoverage = computed(() => loadingIds.value.size > 0)
const loadTokens = new Map<string, number>()    // id → generation counter for cancellation
let hasAutoFit = false

// ── Icons ───────────────────────────────────────────────────────────────────

function makeIcon(color: string) {
  return L.divIcon({
    html: `<div style="
      width:20px;height:20px;border-radius:50% 50% 50% 0;
      background:${color};border:2px solid white;
      transform:rotate(-45deg);box-shadow:0 2px 6px rgba(0,0,0,.4)">
    </div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 20],
    className: '',
  })
}

const deployedIcon = makeIcon('#198754')   // green
const plannedIcon  = makeIcon('#fd7e14')   // orange
const draftIcon    = makeIcon('#6c757d')   // muted gray — creator-only draft
const ghostIcon    = makeIcon('#9e9e9e')   // gray — pending/unsaved position

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  map = L.map(mapEl.value!, { zoom: 10, zoomControl: false })
  map.setView([42.35, 14.1], 10)   // Pescara, Abruzzo

  L.control.zoom({ position: 'bottomleft' }).addTo(map)

  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
  })
  const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: 'Map data: © OpenStreetMap, SRTM | OpenTopoMap',
  })
  const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { attribution: 'Tiles © Esri' }
  )

  osm.addTo(map)
  L.control.layers({ OSM: osm, Topo: topo, Satellite: satellite }, {}, { position: 'bottomleft' }).addTo(map)

  markersLayer = L.layerGroup().addTo(map)
  pathLayer = L.layerGroup().addTo(map)

  map.on('click', (e) => {
    emit('mapClick', e.latlng.lat, e.latlng.lng)
  })

  renderMarkers()
})

// ── Watchers ─────────────────────────────────────────────────────────────────

watch(() => props.nodes, (nodes) => {
  renderMarkers()
  // Auto-fit when nodes first load (map was at default center before)
  if (nodes.length > 0 && !hasAutoFit) {
    hasAutoFit = true
    fitNodes()
  }
}, { deep: true })
watch(() => props.pathResult, renderPath, { deep: true })
// Watch a serialized snapshot so Vue correctly detects Set mutations
watch(
  () => [...props.visibleCoverage].sort().join(','),
  () => syncCoverage(),
)
watch(() => uiStore.privacyMode, () => { renderMarkers(); renderPath() })

// ── Rendering ────────────────────────────────────────────────────────────────

function renderMarkers() {
  if (!markersLayer) return
  markersLayer.clearLayers()
  const privacy = uiStore.privacyMode
  for (const node of props.nodes) {
    const pos = privacy ? fuzzCoords(node.lat, node.lon, node.id) : { lat: node.lat, lon: node.lon }
    const icon = node.status === 'deployed' ? deployedIcon : node.status === 'planned' ? plannedIcon : draftIcon
    const marker = L.marker([pos.lat, pos.lon], { icon, alt: `${node.name} (${node.status})` })
    marker.bindPopup(`
      <strong>${node.name}</strong><br/>
      ${node.hardware.name}<br/>
      ${t('node.status.label')}: <em>${t(`node.status.${node.status}`)}</em><br/>
      TX: ${node.hardware.tx_power_dbm} dBm &nbsp;|&nbsp; ${node.hardware.frequency_mhz} MHz
      ${node.notes ? `<br/><small>${node.notes}</small>` : ''}
    `)
    marker.on('click', () => emit('nodeClick', node.id))
    markersLayer.addLayer(marker)
  }
}

function renderPath() {
  if (!pathLayer) return
  pathLayer.clearLayers()
  if (!props.pathResult?.found) return

  const privacy = uiStore.privacyMode
  const coords = props.pathResult.hops.map(h => {
    const p = privacy ? fuzzCoords(h.lat, h.lon, h.node_id ?? h.name) : { lat: h.lat, lon: h.lon }
    return [p.lat, p.lon] as L.LatLngTuple
  })
  L.polyline(coords, { color: '#0d6efd', weight: 3, dashArray: '8 4' }).addTo(pathLayer)

  props.pathResult.hops.forEach((hop, i) => {
    const pos = privacy ? fuzzCoords(hop.lat, hop.lon, hop.node_id ?? hop.name) : { lat: hop.lat, lon: hop.lon }
    const label = i === 0 ? 'A' : i === props.pathResult!.hops.length - 1 ? 'B' : `R${i}`
    const icon = L.divIcon({
      html: `<div style="background:#0d6efd;color:#fff;border-radius:50%;width:22px;height:22px;
              display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;
             box-shadow:0 2px 4px rgba(0,0,0,.4)">${label}</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
      className: '',
    })
    const snrText = hop.snr_db !== null ? `${t('path.snr_to_next')}: ${hop.snr_db} dB` : ''
    L.marker([pos.lat, pos.lon], { icon })
      .bindPopup(`<strong>${hop.name}</strong>${snrText ? `<br/>${snrText}` : ''}`)
      .addTo(pathLayer)
  })
}

function syncCoverage() {
  if (!map) return

  const desired = new Set(props.visibleCoverage)

  // Remove layers and cancel any in-flight loads for ids no longer desired
  for (const [id, layer] of rasterLayers) {
    if (!desired.has(id)) {
      map.removeLayer(layer)
      rasterLayers.delete(id)
      loadTokens.set(id, (loadTokens.get(id) ?? 0) + 1)
    }
  }

  // Start a load for each desired id not already on map or in flight
  for (const id of desired) {
    if (!rasterLayers.has(id) && !loadingIds.value.has(id)) {
      loadRasterLayer(id)
    }
  }
}

async function loadRasterLayer(id: string) {
  const myToken = (loadTokens.get(id) ?? 0) + 1
  loadTokens.set(id, myToken)
  loadingIds.value.add(id)
  try {
    const token = authStore.accessToken
    const res = await fetch(`/api/coverage/${id}/geotiff`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) return
    const buf = await res.arrayBuffer()

    // Abort if a newer request superseded this one
    if (loadTokens.get(id) !== myToken) return

    const gr = await parseGeoraster(buf)

    // Abort if superseded during parse, or already added by another call
    if (loadTokens.get(id) !== myToken || rasterLayers.has(id)) return

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const layer = new GeoRasterLayer({ georaster: gr, opacity: 0.65, noDataValue: 255, resolution: 256 } as any)
    layer.addTo(map)
    rasterLayers.set(id, layer)
  } catch {
    // coverage not ready yet
  } finally {
    loadingIds.value.delete(id)
  }
}

// ── Ghost marker ─────────────────────────────────────────────────────────────

let ghostMarker: L.Marker | null = null

watch(() => props.ghostPosition, (pos) => {
  if (!map) return
  if (ghostMarker) {
    map.removeLayer(ghostMarker)
    ghostMarker = null
  }
  if (pos) {
    ghostMarker = L.marker([pos.lat, pos.lon], { icon: ghostIcon })
    const coordText = `${pos.lat.toFixed(5)}, ${pos.lon.toFixed(5)}`
    const isGuest = !authStore.isAuthenticated
    const loginBtn = isGuest
      ? `<br/><button
           id="ghost-login-btn"
           style="margin-top:6px;padding:4px 10px;font-size:.8rem;border:1px solid #0d6efd;
                  background:#0d6efd;color:#fff;border-radius:4px;cursor:pointer">
           ${t('map.login_to_save')}
         </button>`
      : ''
    ghostMarker.bindPopup(
      `<strong style="color:#333">${t('map.new_node_here')}</strong><br/><small style="color:#666">${coordText}</small>${loginBtn}`
    )
    if (isGuest) {
      ghostMarker.on('popupopen', () => {
        const btn = document.getElementById('ghost-login-btn')
        btn?.addEventListener('click', () => emit('loginRequest'))
      })
    }
    ghostMarker.addTo(map)
    ghostMarker.openPopup()
  }
})

// ── Public API ───────────────────────────────────────────────────────────────

function fitNodes() {
  if (!map || props.nodes.length === 0) return
  const bounds = L.latLngBounds(props.nodes.map(n => [n.lat, n.lon] as L.LatLngTuple))
  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
}

function centerOn(id: string) {
  if (!map) return
  const node = props.nodes.find(n => n.id === id)
  if (!node) return
  map.setView([node.lat, node.lon], Math.max(map.getZoom(), 13))
}

defineExpose({ fitNodes, centerOn })
</script>

<style scoped>
#map {
  height: 100%;
  width: 100%;
}
.coverage-loading-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  background: rgba(255,255,255,.92);
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: .8rem;
  color: #495057;
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
  display: flex;
  align-items: center;
}
</style>
