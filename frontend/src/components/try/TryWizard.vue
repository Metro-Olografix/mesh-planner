<template>
  <div class="try-wizard">
    <!-- Step indicator -->
    <div class="wizard-steps">
      <div
        v-for="(label, i) in stepLabels"
        :key="i"
        class="wizard-step"
        :class="{
          'wizard-step--active': step === i + 1,
          'wizard-step--done': step > i + 1,
        }"
      >
        <span class="wizard-step-dot">{{ step > i + 1 ? '✓' : i + 1 }}</span>
        <span class="wizard-step-label">{{ label }}</span>
      </div>
    </div>

    <!-- Step content -->
    <div class="wizard-body">

      <!-- Step 1: Location -->
      <div v-if="step === 1" class="wizard-pane">
        <h5 class="wizard-title">{{ $t('try.location.instruction') }}</h5>
        <p class="wizard-tip">
          <span class="tip-icon">💡</span> {{ $t('try.location.tip') }}
        </p>
        <div v-if="pickedLat !== undefined" class="location-badge">
          <span class="location-dot"></span>
          {{ $t('try.location.selected') }}: {{ formatCoord(pickedLat) }}, {{ formatCoord(pickedLon!) }}
        </div>
        <div v-else class="location-none text-muted small">
          {{ $t('try.location.none_selected') }}
        </div>
      </div>

      <!-- Step 2: Device -->
      <div v-if="step === 2" class="wizard-pane">
        <h5 class="wizard-title">{{ $t('try.device.instruction') }}</h5>
        <p class="wizard-tip">
          <span class="tip-icon">💡</span> {{ $t('try.device.tip') }}
        </p>

        <!-- Recommended shortcut -->
        <div class="recommended-row mb-2">
          <span class="text-muted small">{{ $t('try.device.recommended_hint') }}</span>
          <div class="d-flex gap-1 flex-wrap mt-1">
            <button
              v-for="id in RECOMMENDED_IDS"
              :key="id"
              class="btn btn-sm"
              :class="form.hardware_id === id ? 'btn-primary' : 'btn-outline-primary'"
              @click="form.hardware_id = id"
            >
              {{ hardwareById(id)?.name ?? id }}
            </button>
          </div>
        </div>

        <input
          v-model="hwFilter"
          type="search"
          class="form-control form-control-sm mb-2"
          :placeholder="$t('try.device.search_placeholder')"
        />

        <div class="hw-list">
          <button
            v-for="hw in filteredHardware"
            :key="hw.id"
            class="hw-item"
            :class="{ 'hw-item--selected': form.hardware_id === hw.id }"
            @click="form.hardware_id = hw.id"
          >
            <div class="hw-item-header">
              <span class="hw-item-name">{{ hw.manufacturer }} {{ hw.name }}</span>
              <span v-if="RECOMMENDED_IDS.includes(hw.id)" class="badge bg-success ms-1" style="font-size:.65rem">
                {{ $t('try.device.recommended_badge') }}
              </span>
            </div>
            <div class="hw-item-specs text-muted">
              {{ $t('try.device.specs', {
                tx: hw.tx_power_dbm,
                sensitivity: hw.rx_sensitivity_dbm,
                freq: hw.frequency_mhz,
              }) }}
            </div>
          </button>
        </div>
      </div>

      <!-- Step 3: Setup -->
      <div v-if="step === 3" class="wizard-pane">
        <h5 class="wizard-title">{{ $t('try.step_setup') }}</h5>

        <!-- Height -->
        <div class="mb-3">
          <label class="form-label small fw-semibold mb-1">{{ $t('try.setup.height_label') }}</label>
          <p class="wizard-tip mb-1">
            <span class="tip-icon">💡</span> {{ $t('try.setup.height_tip') }}
          </p>
          <div class="d-flex align-items-center gap-2 mb-1">
            <input
              v-model.number="form.height_m"
              type="range"
              min="1"
              max="30"
              step="1"
              class="form-range flex-fill"
            />
            <span class="fw-semibold" style="width:3rem;text-align:right">{{ form.height_m }} m</span>
          </div>
          <div class="height-presets d-flex flex-wrap gap-1 mb-1">
            <button
              v-for="preset in heightPresets"
              :key="preset.value"
              class="btn btn-xs"
              :class="form.height_m === preset.value ? 'btn-secondary' : 'btn-outline-secondary'"
              @click="form.height_m = preset.value"
            >
              {{ preset.label }}
            </button>
          </div>
          <div class="text-muted" style="font-size:.75rem">
            {{ floorHint }}
          </div>
        </div>

        <!-- Environment -->
        <div class="mb-3">
          <label class="form-label small fw-semibold mb-1">{{ $t('try.setup.environment_label') }}</label>
          <p class="wizard-tip mb-1">
            <span class="tip-icon">💡</span> {{ $t('try.setup.environment_tip') }}
          </p>
          <div class="env-options">
            <label
              v-for="opt in environmentOptions"
              :key="opt.value"
              class="env-option"
              :class="{ 'env-option--selected': form.environment === opt.value }"
            >
              <input
                type="radio"
                :value="opt.value"
                v-model="form.environment"
                class="visually-hidden"
              />
              <span class="env-icon">{{ opt.icon }}</span>
              <span>{{ opt.label }}</span>
            </label>
          </div>
        </div>

        <!-- Range vs Speed -->
        <div class="mb-1">
          <label class="form-label small fw-semibold mb-1">{{ $t('try.setup.range_label') }}</label>
          <p class="wizard-tip mb-1">
            <span class="tip-icon">💡</span> {{ $t('try.setup.range_tip') }}
          </p>
          <div class="range-speed-group">
            <label
              v-for="opt in rangeOptions"
              :key="opt.preset"
              class="range-option"
              :class="{ 'range-option--selected': form.lora_preset === opt.preset }"
            >
              <input
                type="radio"
                :value="opt.preset"
                v-model="form.lora_preset"
                class="visually-hidden"
              />
              <span class="range-option-label">{{ opt.label }}</span>
              <span class="range-option-detail">{{ opt.detail }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Step 4: Results -->
      <div v-if="step === 4" class="wizard-pane">
        <!-- Computing -->
        <div v-if="computing" class="text-center py-3">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="fw-semibold mb-1">{{ $t('try.results.computing') }}</p>
          <p class="text-muted small mb-2">{{ $t('try.results.computing_detail') }}</p>
          <div class="computing-steps">
            <div
              v-for="(s, i) in computingSteps"
              :key="i"
              class="computing-step"
              :class="{ 'computing-step--active': computingStepIdx === i, 'computing-step--done': computingStepIdx > i }"
            >
              <span>{{ computingStepIdx > i ? '✓' : '·' }}</span> {{ s }}
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="errorMsg" class="alert alert-warning mb-2">
          {{ errorMsg }}
        </div>

        <!-- Results ready -->
        <div v-else-if="coverageReady">
          <!-- Legend -->
          <div class="legend-card mb-2">
            <div class="legend-title fw-semibold small mb-1">{{ $t('try.results.legend_title') }}</div>
            <div class="legend-bar"></div>
            <div class="d-flex justify-content-between" style="font-size:.72rem;color:#666">
              <span>{{ $t('try.results.legend_weak') }}</span>
              <span>{{ $t('try.results.legend_strong') }}</span>
            </div>
            <p class="text-muted mt-1 mb-0" style="font-size:.72rem">{{ $t('try.results.legend_detail') }}</p>
            <p class="text-muted mb-0" style="font-size:.72rem">
              {{ $t('try.results.radius_note', { radius: maxRadiusKm }) }}
            </p>
          </div>

          <!-- Share -->
          <div v-if="shareableUrl" class="share-card mb-2">
            <div class="d-flex align-items-center gap-2">
              <span class="small fw-semibold flex-fill">{{ $t('try.share') }}</span>
              <button
                class="btn btn-sm"
                :class="copied ? 'btn-success' : 'btn-outline-secondary'"
                style="font-size:.75rem;padding:2px 10px"
                @click="copyLink"
              >
                {{ copied ? $t('try.copied') : $t('try.copy_link') }}
              </button>
            </div>
            <div class="share-url mt-1">{{ shareableUrl }}</div>
            <p class="text-muted mb-0 mt-1" style="font-size:.7rem">{{ $t('try.share_tip') }}</p>
          </div>

          <!-- CTA -->
          <div class="cta-card">
            <p class="fw-semibold mb-1">{{ $t('try.join_cta') }}</p>
            <p class="text-muted small mb-2">{{ $t('try.join_detail') }}</p>
            <a
              :href="ctaUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="btn btn-primary btn-sm w-100"
            >
              {{ $t('try.join_cta') }} →
            </a>
          </div>
        </div>
      </div>

      <!-- Error banner (non-step-4 errors) -->
      <div v-if="step !== 4 && errorMsg" class="alert alert-warning mt-2 mb-0 py-2 small">
        {{ errorMsg }}
      </div>
    </div>

    <!-- Footer buttons -->
    <div class="wizard-footer">
      <template v-if="step < 4">
        <button
          v-if="step > 1"
          class="btn btn-outline-secondary btn-sm"
          @click="step--; errorMsg = ''"
        >
          {{ $t('try.back') }}
        </button>
        <div class="flex-fill"></div>
        <button
          v-if="step < 3"
          class="btn btn-primary btn-sm"
          :disabled="!canAdvance"
          @click="advance"
        >
          {{ $t('try.next') }}
        </button>
        <button
          v-if="step === 3"
          class="btn btn-primary btn-sm"
          :disabled="!canAdvance || computing"
          @click="runSimulation"
        >
          {{ $t('try.run') }}
        </button>
      </template>
      <template v-else>
        <button class="btn btn-outline-secondary btn-sm" @click="reset">
          {{ $t('try.try_again') }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import type { HardwareProfile } from '../../types'

const { t, locale } = useI18n()

const props = defineProps<{
  pickedLat?: number
  pickedLon?: number
  maxRadiusKm: number
  initialHardwareId?: string
  initialHeightM?: number
  initialEnvironment?: string
  initialLoraPreset?: string
  autoRun?: boolean
  shareableUrl?: string
}>()

const emit = defineEmits<{
  coverageReady: [buf: ArrayBuffer]
  coverageCleared: []
  paramsReady: [params: { hardware_id: string; height_m: number; environment: string; lora_preset: string }]
  reset: []
}>()

// ── Constants ────────────────────────────────────────────────────────────────
const RECOMMENDED_IDS = ['heltec-v3', 'rak4631']

// ── State ────────────────────────────────────────────────────────────────────
const step = ref(1)
const hardware = ref<HardwareProfile[]>([])
const hwFilter = ref('')
const computing = ref(false)
const coverageReady = ref(false)
const errorMsg = ref('')
const computingStepIdx = ref(0)
const copied = ref(false)
const hasAutoRun = ref(false)

const form = ref({
  hardware_id: props.initialHardwareId ?? 'heltec-v3',
  height_m: props.initialHeightM ?? 3,
  environment: (props.initialEnvironment ?? 'auto') as 'auto' | 'urban' | 'suburban' | 'rural' | 'open',
  lora_preset: props.initialLoraPreset ?? 'MEDIUM_FAST',
})

// ── Computed ─────────────────────────────────────────────────────────────────
const ctaUrl = computed(() =>
  locale.value === 'it'
    ? 'https://olografix.org/associazione/associati/'
    : 'https://olografix.org/en/association/join-us/'
)

const stepLabels = computed(() => [
  t('try.step_location'),
  t('try.step_device'),
  t('try.step_setup'),
  t('try.step_results'),
])

const canAdvance = computed(() => {
  if (step.value === 1) return props.pickedLat !== undefined
  if (step.value === 2) return !!form.value.hardware_id
  if (step.value === 3) return !!form.value.hardware_id
  return false
})

const filteredHardware = computed(() => {
  const q = hwFilter.value.toLowerCase()
  const list = q
    ? hardware.value.filter(h =>
        `${h.manufacturer} ${h.name}`.toLowerCase().includes(q)
      )
    : hardware.value
  // Recommended devices first
  return [...list].sort((a, b) => {
    const aR = RECOMMENDED_IDS.includes(a.id) ? 0 : 1
    const bR = RECOMMENDED_IDS.includes(b.id) ? 0 : 1
    return aR - bR
  })
})

const floorHint = computed(() => {
  const h = form.value.height_m
  const floors = Math.round((h - 1) / 3)
  if (floors <= 0) return t('try.setup.height_hint_ground')
  return t('try.setup.height_hint', { floors })
})

const computingSteps = computed(() => [
  t('try.results.computing_step1'),
  t('try.results.computing_step2'),
  t('try.results.computing_step3'),
])

const heightPresets = computed(() => [
  { value: 1,  label: '1 m' },
  { value: 3,  label: '~3 m' },
  { value: 6,  label: '~6 m' },
  { value: 9,  label: '~9 m' },
  { value: 15, label: '~15 m' },
  { value: 20, label: '20 m+' },
])

const environmentOptions = computed(() => [
  { value: 'auto',     icon: '🛰️', label: t('try.setup.environment_options.auto') },
  { value: 'urban',    icon: '🏙️', label: t('try.setup.environment_options.urban') },
  { value: 'suburban', icon: '🏘️', label: t('try.setup.environment_options.suburban') },
  { value: 'rural',    icon: '🌾', label: t('try.setup.environment_options.rural') },
  { value: 'open',     icon: '⛰️', label: t('try.setup.environment_options.open') },
])

const rangeOptions = computed(() => [
  { preset: 'SHORT_FAST',  label: t('try.setup.range_fast'),     detail: t('try.setup.range_fast_detail') },
  { preset: 'MEDIUM_FAST', label: t('try.setup.range_balanced'), detail: t('try.setup.range_balanced_detail') },
  { preset: 'LONG_SLOW',   label: t('try.setup.range_long'),     detail: t('try.setup.range_long_detail') },
])

// ── Helpers ──────────────────────────────────────────────────────────────────
function hardwareById(id: string) {
  return hardware.value.find(h => h.id === id)
}

function formatCoord(n: number) {
  return n.toFixed(5)
}

async function copyLink() {
  if (!props.shareableUrl) return
  try {
    await navigator.clipboard.writeText(props.shareableUrl)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // Clipboard API not available — fallback: select the text
  }
}

// ── Auto-run when parent has set a location from URL params ──────────────────
watch(() => props.pickedLat, (lat) => {
  if (props.autoRun && lat !== undefined && !hasAutoRun.value) {
    hasAutoRun.value = true
    nextTick(() => runSimulation())
  }
})

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await fetch('/api/hardware/')
    if (res.ok) hardware.value = await res.json()
  } catch {
    // non-fatal
  }
})

// ── Actions ──────────────────────────────────────────────────────────────────
function advance() {
  errorMsg.value = ''
  if (step.value < 4) step.value++
}

async function runSimulation() {
  if (!props.pickedLat || !props.pickedLon) {
    errorMsg.value = t('try.errors.no_location')
    return
  }
  if (!form.value.hardware_id) {
    errorMsg.value = t('try.errors.no_device')
    return
  }

  errorMsg.value = ''
  step.value = 4
  computing.value = true
  coverageReady.value = false
  computingStepIdx.value = 0

  // Notify parent so it can update the browser URL
  emit('paramsReady', {
    hardware_id: form.value.hardware_id,
    height_m: form.value.height_m,
    environment: form.value.environment,
    lora_preset: form.value.lora_preset,
  })

  const stepInterval = setInterval(() => {
    if (computingStepIdx.value < computingSteps.value.length - 1) {
      computingStepIdx.value++
    }
  }, 4000)

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 60_000)

  try {
    const res = await fetch('/api/try/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: props.pickedLat,
        lon: props.pickedLon,
        hardware_id: form.value.hardware_id,
        height_m: form.value.height_m,
        environment: form.value.environment,
        lora_preset: form.value.lora_preset,
      }),
      signal: controller.signal,
    })

    if (res.status === 429) {
      errorMsg.value = t('try.errors.rate_limit', { limit: 3 })
      return
    }
    if (res.status === 503) {
      errorMsg.value = t('try.errors.busy')
      return
    }
    if (!res.ok) {
      errorMsg.value = t('try.errors.failed')
      return
    }

    const buf = await res.arrayBuffer()
    computingStepIdx.value = computingSteps.value.length - 1
    coverageReady.value = true
    emit('coverageReady', buf)
  } catch (err: unknown) {
    errorMsg.value = t('try.errors.failed')
  } finally {
    clearInterval(stepInterval)
    clearTimeout(timeout)
    computing.value = false
  }
}

function reset() {
  step.value = 1
  computing.value = false
  coverageReady.value = false
  errorMsg.value = ''
  computingStepIdx.value = 0
  copied.value = false
  hasAutoRun.value = false
  emit('reset')
}
</script>

<style scoped>
.try-wizard {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.15);
  overflow: hidden;
}

/* ── Step indicator ─────────────────────────────────────────────────────── */
.wizard-steps {
  display: flex;
  border-bottom: 1px solid #e9ecef;
  background: #f8f9fa;
  padding: 10px 12px 8px;
  gap: 4px;
  flex-shrink: 0;
}
.wizard-step {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  opacity: .4;
  transition: opacity .2s;
  min-width: 0;
}
.wizard-step--active { opacity: 1; }
.wizard-step--done { opacity: .7; }
.wizard-step-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #dee2e6;
  font-size: .7rem;
  font-weight: 700;
  flex-shrink: 0;
  color: #495057;
}
.wizard-step--active .wizard-step-dot {
  background: #0d6efd;
  color: #fff;
}
.wizard-step--done .wizard-step-dot {
  background: #198754;
  color: #fff;
}
.wizard-step-label {
  font-size: .7rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #495057;
}

/* ── Body ───────────────────────────────────────────────────────────────── */
.wizard-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.wizard-pane { display: flex; flex-direction: column; gap: 4px; }
.wizard-title { font-size: .95rem; font-weight: 600; margin-bottom: 4px; }
.wizard-tip {
  font-size: .78rem;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 7px 10px;
  margin-bottom: 8px;
  line-height: 1.4;
}
.tip-icon { margin-right: 4px; }

.location-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: .82rem;
  font-weight: 500;
  background: #e8f5e9;
  border: 1px solid #c8e6c9;
  border-radius: 6px;
  padding: 8px 12px;
  color: #2e7d32;
}
.location-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #198754;
  flex-shrink: 0;
}
.location-none { padding: 8px 0; }

/* ── Hardware list ──────────────────────────────────────────────────────── */
.recommended-row {
  background: #f0f7ff;
  border: 1px solid #cfe2ff;
  border-radius: 6px;
  padding: 8px 10px;
}
.hw-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
}
.hw-item {
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 7px 10px;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.hw-item:hover { border-color: #0d6efd; background: #f0f7ff; }
.hw-item--selected { border-color: #0d6efd; background: #e8f0fe; }
.hw-item-header { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.hw-item-name { font-size: .82rem; font-weight: 600; }
.hw-item-specs { font-size: .72rem; margin-top: 2px; }

/* ── Height presets ─────────────────────────────────────────────────────── */
.btn-xs {
  font-size: .72rem;
  padding: 1px 8px;
  border-radius: 4px;
  border: 1px solid #6c757d;
  background: transparent;
  color: #495057;
  cursor: pointer;
  line-height: 1.6;
}
.btn-xs.btn-secondary { background: #6c757d; color: #fff; border-color: #6c757d; }
.btn-xs.btn-outline-secondary:hover { background: #f8f9fa; }

/* ── Environment options ────────────────────────────────────────────────── */
.env-options { display: flex; flex-direction: column; gap: 4px; }
.env-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  font-size: .82rem;
  transition: border-color .15s, background .15s;
}
.env-option:hover { border-color: #0d6efd; background: #f0f7ff; }
.env-option--selected { border-color: #0d6efd; background: #e8f0fe; font-weight: 600; }
.env-icon { font-size: 1.1rem; flex-shrink: 0; }

/* ── Range/speed options ────────────────────────────────────────────────── */
.range-speed-group { display: flex; gap: 6px; }
.range-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 6px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  text-align: center;
  transition: border-color .15s, background .15s;
}
.range-option:hover { border-color: #0d6efd; background: #f0f7ff; }
.range-option--selected { border-color: #0d6efd; background: #e8f0fe; }
.range-option-label { font-size: .82rem; font-weight: 600; }
.range-option-detail { font-size: .68rem; color: #6c757d; margin-top: 2px; line-height: 1.3; }

/* ── Computing steps ────────────────────────────────────────────────────── */
.computing-steps { display: flex; flex-direction: column; gap: 4px; margin-top: 4px; }
.computing-step { font-size: .78rem; color: #6c757d; transition: color .3s; }
.computing-step--active { color: #0d6efd; font-weight: 600; }
.computing-step--done { color: #198754; }

/* ── Legend ─────────────────────────────────────────────────────────────── */
.legend-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 10px 12px;
}
.legend-bar {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(to right, #0d0887, #6e00a8, #b12a90, #e16462, #fca636, #f0f921);
  margin-bottom: 4px;
}

/* ── Share card ─────────────────────────────────────────────────────────── */
.share-card {
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 8px;
  padding: 10px 12px;
}
.share-url {
  font-family: monospace;
  font-size: .68rem;
  color: #555;
  word-break: break-all;
  background: rgba(0,0,0,.04);
  border-radius: 4px;
  padding: 4px 6px;
  line-height: 1.5;
}

/* ── CTA ────────────────────────────────────────────────────────────────── */
.cta-card {
  background: linear-gradient(135deg, #e8f5e9, #f0f7ff);
  border: 1px solid #c8e6c9;
  border-radius: 8px;
  padding: 12px 14px;
}

/* ── Footer ─────────────────────────────────────────────────────────────── */
.wizard-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
  flex-shrink: 0;
}
</style>
