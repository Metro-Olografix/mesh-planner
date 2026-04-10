<template>
  <div class="try-layout">
    <!-- Top bar -->
    <nav class="try-nav">
      <a href="/" class="try-nav-back">
        ← {{ $t('try.back_to_planner') }}
      </a>
      <span class="try-nav-title">
        <span aria-hidden="true">📡</span> {{ $t('try.page_title') }}
      </span>
      <button class="try-nav-lang" @click="toggleLanguage">{{ locale.toUpperCase() }}</button>
    </nav>

    <!-- Body: map + wizard -->
    <div class="try-body">
      <!-- Map -->
      <div id="try-map" ref="mapEl" class="try-map"></div>

      <!-- Loading badge for coverage -->
      <div v-if="loadingCoverage" class="coverage-loading-badge">
        <span class="spinner-border spinner-border-sm me-1" role="status"></span>
        {{ $t('map.loading_coverage') }}
      </div>

      <!-- Click-to-place hint (step 1) -->
      <div v-if="showClickHint && !pickedLat" class="map-click-hint">
        {{ $t('try.location.instruction') }}
      </div>

      <!-- Wizard panel -->
      <div class="wizard-panel">
        <TryWizard
          :picked-lat="pickedLat"
          :picked-lon="pickedLon"
          :max-radius-km="MAX_RADIUS_KM"
          :initial-hardware-id="initialForm.hardware_id"
          :initial-height-m="initialForm.height_m"
          :initial-environment="initialForm.environment"
          :initial-lora-preset="initialForm.lora_preset"
          :auto-run="autoRun"
          :shareable-url="shareableUrl"
          @coverage-ready="onCoverageReady"
          @coverage-cleared="clearCoverage"
          @params-ready="onParamsReady"
          @reset="onReset"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import GeoRasterLayer from 'georaster-layer-for-leaflet'
import parseGeoraster from 'georaster'
import { setLanguage } from '../i18n'
import TryWizard from '../components/try/TryWizard.vue'

const { locale } = useI18n()
const route = useRoute()

const MAX_RADIUS_KM = 3 // matches backend default

// ── Map state ────────────────────────────────────────────────────────────────
const mapEl = ref<HTMLElement>()
let map: L.Map
let pickedMarker: L.Marker | null = null
let rasterLayer: any = null

const pickedLat = ref<number | undefined>()
const pickedLon = ref<number | undefined>()
const loadingCoverage = ref(false)
const showClickHint = ref(true)

// ── Pre-fill from URL query params ───────────────────────────────────────────
interface InitialForm {
  hardware_id?: string
  height_m?: number
  environment?: string
  lora_preset?: string
}
const initialForm = ref<InitialForm>({})
const autoRun = ref(false)

// ── Shareable URL ────────────────────────────────────────────────────────────
const lastParams = ref<Record<string, string>>({})

const shareableUrl = computed(() => {
  if (!pickedLat.value || !pickedLon.value || !lastParams.value.hw) return ''
  const q = new URLSearchParams({
    lat: pickedLat.value.toFixed(6),
    lon: pickedLon.value.toFixed(6),
    ...lastParams.value,
  })
  return `${window.location.origin}/try?${q.toString()}`
})

function onParamsReady(params: {
  hardware_id: string
  height_m: number
  environment: string
  lora_preset: string
}) {
  lastParams.value = {
    hw: params.hardware_id,
    h: String(params.height_m),
    env: params.environment,
    preset: params.lora_preset,
  }
  // Update browser URL without a navigation so the link is shareable
  if (pickedLat.value && pickedLon.value) {
    const q = new URLSearchParams({
      lat: pickedLat.value.toFixed(6),
      lon: pickedLon.value.toFixed(6),
      ...lastParams.value,
    })
    history.replaceState(null, '', `/try?${q.toString()}`)
  }
}

// ── Language ──────────────────────────────────────────────────────────────────
function toggleLanguage() {
  const next = locale.value === 'en' ? 'it' : 'en'
  setLanguage(next)
}

// ── Marker icon ───────────────────────────────────────────────────────────────
const pickedIcon = L.divIcon({
  html: `<div style="
    width:22px;height:22px;border-radius:50% 50% 50% 0;
    background:#0d6efd;border:3px solid white;
    transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,.4)">
  </div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 22],
  className: '',
})

// ── Map lifecycle ─────────────────────────────────────────────────────────────
onMounted(() => {
  map = L.map(mapEl.value!, { zoom: 9, zoomControl: false })
  map.setView([42.35, 14.1], 9)

  L.control.zoom({ position: 'bottomright' }).addTo(map)

  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
  })
  const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: 'Map data: © OpenStreetMap, SRTM | OpenTopoMap',
  })
  const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { attribution: 'Tiles © Esri' },
  )

  osm.addTo(map)
  L.control.layers({ OSM: osm, Topo: topo, Satellite: satellite }, {}, { position: 'bottomright' }).addTo(map)

  map.on('click', (e) => {
    pickedLat.value = e.latlng.lat
    pickedLon.value = e.latlng.lng
    showClickHint.value = false
    placeMarker(e.latlng.lat, e.latlng.lng)
    // Clear stale shared URL when user picks a new location manually
    lastParams.value = {}
    history.replaceState(null, '', '/try')
  })

  // Read query params and pre-fill
  const q = route.query
  const lat = parseFloat(q.lat as string)
  const lon = parseFloat(q.lon as string)
  const hw = q.hw as string | undefined
  const h = parseFloat(q.h as string)
  const env = q.env as string | undefined
  const preset = q.preset as string | undefined

  if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
    pickedLat.value = lat
    pickedLon.value = lon
    showClickHint.value = false
    placeMarker(lat, lon)
    map.setView([lat, lon], 12)
  }

  if (hw) initialForm.value.hardware_id = hw
  if (!isNaN(h) && h >= 1 && h <= 30) initialForm.value.height_m = h
  if (env && ['auto', 'urban', 'suburban', 'rural', 'open'].includes(env)) initialForm.value.environment = env
  if (preset && ['SHORT_FAST', 'SHORT_SLOW', 'MEDIUM_FAST', 'MEDIUM_SLOW', 'LONG_FAST', 'LONG_SLOW', 'VERY_LONG_SLOW'].includes(preset)) {
    initialForm.value.lora_preset = preset
  }

  // Auto-run if all params are present in the URL
  if (!isNaN(lat) && !isNaN(lon) && hw && !isNaN(h) && env && preset) {
    lastParams.value = { hw, h: String(Math.round(h)), env, preset }
    autoRun.value = true
  }
})

onUnmounted(() => {
  map?.remove()
})

// ── Marker management ─────────────────────────────────────────────────────────
function placeMarker(lat: number, lon: number) {
  if (pickedMarker) {
    pickedMarker.setLatLng([lat, lon])
  } else {
    pickedMarker = L.marker([lat, lon], { icon: pickedIcon }).addTo(map)
  }
}

// ── Coverage rendering ────────────────────────────────────────────────────────
async function onCoverageReady(buf: ArrayBuffer) {
  clearCoverage()
  loadingCoverage.value = true
  try {
    const gr = await parseGeoraster(buf)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    rasterLayer = new GeoRasterLayer({ georaster: gr, opacity: 0.7, noDataValue: 255, resolution: 256 } as any)
    rasterLayer.addTo(map)
    // Use georaster metadata bounds directly — more reliable than rasterLayer.getBounds()
    // before the layer has fully rendered. flyToBounds gives a smooth animated zoom.
    const bounds = L.latLngBounds([gr.ymin, gr.xmin], [gr.ymax, gr.xmax])
    map.flyToBounds(bounds, { padding: [40, 40], duration: 1.2 })
  } catch {
    // parse failure — coverage just won't appear, not fatal
  } finally {
    loadingCoverage.value = false
  }
}

function clearCoverage() {
  if (rasterLayer) {
    map.removeLayer(rasterLayer)
    rasterLayer = null
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────
function onReset() {
  clearCoverage()
  if (pickedMarker) {
    map.removeLayer(pickedMarker)
    pickedMarker = null
  }
  pickedLat.value = undefined
  pickedLon.value = undefined
  showClickHint.value = true
  lastParams.value = {}
  autoRun.value = false
  history.replaceState(null, '', '/try')
}
</script>

<style scoped>
.try-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* ── Navbar ──────────────────────────────────────────────────────────────── */
.try-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 16px;
  background: #212529;
  color: #fff;
  flex-shrink: 0;
}
.try-nav-back {
  color: rgba(255,255,255,.7);
  text-decoration: none;
  font-size: .8rem;
  white-space: nowrap;
  transition: color .15s;
}
.try-nav-back:hover { color: #fff; }
.try-nav-title {
  flex: 1;
  font-weight: 600;
  font-size: .9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}
.try-nav-lang {
  background: transparent;
  border: 1px solid rgba(255,255,255,.3);
  color: rgba(255,255,255,.75);
  border-radius: 5px;
  font-size: .75rem;
  padding: 2px 8px;
  cursor: pointer;
  white-space: nowrap;
}
.try-nav-lang:hover { border-color: rgba(255,255,255,.6); color: #fff; }

/* ── Body ────────────────────────────────────────────────────────────────── */
.try-body {
  flex: 1;
  position: relative;
  overflow: hidden;
}

/* ── Map ─────────────────────────────────────────────────────────────────── */
.try-map {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* ── Overlays ────────────────────────────────────────────────────────────── */
.coverage-loading-badge {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 500;
  background: rgba(255,255,255,.92);
  border: 1px solid #dee2e6;
  border-radius: 20px;
  padding: 5px 14px;
  font-size: .8rem;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0,0,0,.12);
  display: flex;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}

.map-click-hint {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 500;
  background: rgba(13,110,253,.9);
  color: #fff;
  border-radius: 20px;
  padding: 6px 16px;
  font-size: .82rem;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
  pointer-events: none;
  white-space: nowrap;
}

/* ── Wizard panel ────────────────────────────────────────────────────────── */
.wizard-panel {
  position: absolute;
  z-index: 400;
  display: flex;
  flex-direction: column;
}

/* Desktop: left sidebar-style panel */
@media (min-width: 768px) {
  .wizard-panel {
    top: 12px;
    left: 12px;
    bottom: 12px;
    width: 360px;
  }
}

/* Mobile: bottom sheet */
@media (max-width: 767.98px) {
  .wizard-panel {
    left: 0;
    right: 0;
    bottom: 0;
    max-height: 55vh;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    box-shadow: 0 -4px 24px rgba(0,0,0,.15);
  }
}
</style>
