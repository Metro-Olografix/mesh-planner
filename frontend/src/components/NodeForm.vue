<template>
  <form @submit.prevent="submit" class="p-3">
    <h6 class="mb-3 fw-semibold">{{ isEdit ? 'Edit node' : 'Add node' }}</h6>

    <div class="mb-2">
      <label class="form-label small mb-1">Name</label>
      <input v-model="form.name" class="form-control form-control-sm" required />
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">Hardware</label>
      <select v-model="form.hardware_id" class="form-select form-select-sm" required @change="onHardwareChange">
        <option value="" disabled>Select hardware…</option>
        <option v-for="hw in hardware" :key="hw.id" :value="hw.id">
          {{ hw.manufacturer }} {{ hw.name }}
        </option>
      </select>
      <div v-if="selectedHardware" class="text-muted" style="font-size:.75rem;margin-top:2px">
        {{ selectedHardware.tx_power_dbm }} dBm TX &nbsp;|&nbsp;
        {{ selectedHardware.rx_sensitivity_dbm }} dBm sensitivity &nbsp;|&nbsp;
        {{ selectedHardware.frequency_mhz }} MHz
      </div>
    </div>

    <div class="row g-2 mb-2">
      <div class="col">
        <label class="form-label small mb-1">Latitude</label>
        <input v-model.number="form.lat" type="number" step="any" class="form-control form-control-sm" required />
      </div>
      <div class="col">
        <label class="form-label small mb-1">Longitude</label>
        <input v-model.number="form.lon" type="number" step="any" class="form-control form-control-sm" required />
      </div>
    </div>

    <div class="row g-2 mb-2">
      <div class="col">
        <label class="form-label small mb-1">Height AGL (m)</label>
        <input v-model.number="form.height_m" type="number" step="0.1" min="0.1" class="form-control form-control-sm" required />
      </div>
      <div class="col">
        <label class="form-label small mb-1">Antenna gain (dBi)</label>
        <input
          v-model.number="form.antenna_gain_dbi"
          type="number" step="0.1"
          class="form-control form-control-sm"
          :placeholder="selectedHardware ? `default: ${selectedHardware.default_antenna_gain_dbi}` : 'dBi'"
        />
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">Clutter environment</label>
      <select v-model="form.environment" class="form-select form-select-sm">
        <option value="auto">Auto-detect from satellite data (recommended)</option>
        <option value="urban">Urban — dense buildings (~10 m)</option>
        <option value="suburban">Suburban — low-rise mixed (~5 m)</option>
        <option value="rural">Rural — scattered structures (~2 m)</option>
        <option value="open">Open — fields, water, airport (~0 m)</option>
      </select>
      <div class="text-muted" style="font-size:.72rem;margin-top:2px">
        Sets the obstacle height used in the RF coverage simulation (SPLAT! -gc flag).
        "Auto" queries ESA WorldCover land-cover data for this location.
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">LoRa preset</label>
      <select v-model="form.lora_preset" class="form-select form-select-sm">
        <option value="SHORT_FAST">SHORT_FAST — SF7, BW500 kHz (fastest, shortest range)</option>
        <option value="SHORT_SLOW">SHORT_SLOW — SF8, BW250 kHz</option>
        <option value="MEDIUM_FAST">MEDIUM_FAST — SF9, BW250 kHz (recommended)</option>
        <option value="MEDIUM_SLOW">MEDIUM_SLOW — SF10, BW250 kHz</option>
        <option value="LONG_FAST">LONG_FAST — SF11, BW250 kHz</option>
        <option value="LONG_SLOW">LONG_SLOW — SF12, BW125 kHz</option>
        <option value="VERY_LONG_SLOW">VERY_LONG_SLOW — SF12, BW125 kHz (slowest, longest range)</option>
      </select>
      <div class="text-muted" style="font-size:.72rem;margin-top:2px">
        Must match the preset configured on the physical device. Affects SNR calculations in path finding.
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">Coverage simulation radius (km)</label>
      <div class="d-flex align-items-center gap-2">
        <input v-model.number="form.sim_radius_km" type="range" min="1" max="50" step="1" class="form-range flex-fill" />
        <span class="text-muted small" style="width:3rem;text-align:right">{{ form.sim_radius_km }} km</span>
      </div>
      <div class="text-muted" style="font-size:.72rem">Larger radius = longer computation time</div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">Status</label>
      <div class="d-flex gap-3">
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="planned" id="s-planned" />
          <label class="form-check-label small" for="s-planned">Planned</label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="deployed" id="s-deployed" />
          <label class="form-check-label small" for="s-deployed">Deployed</label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="draft" id="s-draft" />
          <label class="form-check-label small" for="s-draft">Draft <span class="text-muted">(only you)</span></label>
        </div>
      </div>
    </div>

    <div class="mb-3">
      <label class="form-label small mb-1">Notes</label>
      <textarea v-model="form.notes" class="form-control form-control-sm" rows="2" placeholder="Optional…"></textarea>
    </div>

    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary btn-sm flex-fill" :disabled="saving">
        {{ saving ? 'Saving…' : (isEdit ? 'Save changes' : 'Add node') }}
      </button>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="emit('cancel')">Cancel</button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { HardwareProfile, MeshNode, NodeCreate, NodeEnvironment, NodeStatus, NodeUpdate } from '../types'

const props = defineProps<{
  node?: MeshNode | null
  hardware: HardwareProfile[]
  prefillLat?: number
  prefillLon?: number
}>()

const emit = defineEmits<{
  save: [payload: NodeCreate | NodeUpdate]
  cancel: []
}>()

const isEdit = computed(() => !!props.node)
const saving = ref(false)

const form = ref({
  name: '',
  hardware_id: '',
  lat: props.prefillLat ?? 42.35,
  lon: props.prefillLon ?? 14.1,
  height_m: 2.0,
  antenna_gain_dbi: null as number | null,
  sim_radius_km: 10,
  environment: 'auto' as NodeEnvironment,
  lora_preset: 'MEDIUM_FAST' as NodeCreate['lora_preset'],
  status: 'planned' as NodeStatus,
  notes: '' as string | null,
})

const selectedHardware = computed(() =>
  props.hardware.find(h => h.id === form.value.hardware_id) ?? null
)

watch(() => props.node, (n) => {
  if (!n) return
  form.value = {
    name: n.name,
    hardware_id: n.hardware_id,
    lat: n.lat,
    lon: n.lon,
    height_m: n.height_m,
    antenna_gain_dbi: n.antenna_gain_dbi,
    sim_radius_km: n.sim_radius_km,
    environment: n.environment,
    lora_preset: n.lora_preset,
    status: n.status,
    notes: n.notes,
  }
}, { immediate: true })

watch(() => [props.prefillLat, props.prefillLon], ([lat, lon]) => {
  if (lat !== undefined) form.value.lat = lat
  if (lon !== undefined) form.value.lon = lon
})

function onHardwareChange() {
  form.value.antenna_gain_dbi = null
}

async function submit() {
  saving.value = true
  try {
    const payload: NodeCreate = {
      name: form.value.name,
      hardware_id: form.value.hardware_id,
      lat: form.value.lat,
      lon: form.value.lon,
      height_m: form.value.height_m,
      antenna_gain_dbi: form.value.antenna_gain_dbi || null,
      sim_radius_km: form.value.sim_radius_km,
      environment: form.value.environment,
      lora_preset: form.value.lora_preset,
      status: form.value.status,
      notes: form.value.notes || null,
    }
    emit('save', payload)
  } finally {
    saving.value = false
  }
}
</script>
