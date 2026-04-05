<template>
  <form @submit.prevent="submit" class="p-3">
    <h6 class="mb-3 fw-semibold">{{ isEdit ? $t('node.edit_node') : $t('node.add_node') }}</h6>

    <div class="mb-2">
      <label class="form-label small mb-1">{{ $t('node.form.name') }} <span class="text-danger">*</span></label>
      <input v-model="form.name" class="form-control form-control-sm" required />
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">{{ $t('node.form.hardware') }} <span class="text-danger">*</span></label>
      <select v-model="form.hardware_id" class="form-select form-select-sm" required @change="onHardwareChange">
        <option value="" disabled>{{ $t('node.form.select_hardware') }}</option>
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
        <label class="form-label small mb-1">{{ $t('node.form.latitude') }} <span class="text-danger">*</span></label>
        <input v-if="uiStore.privacyMode && isEdit" class="form-control form-control-sm" disabled value="*****" />
        <input v-else v-model.number="form.lat" type="number" step="any" min="-90" max="90" class="form-control form-control-sm" required :placeholder="$t('node.form.click_map')" />
      </div>
      <div class="col">
        <label class="form-label small mb-1">{{ $t('node.form.longitude') }} <span class="text-danger">*</span></label>
        <input v-if="uiStore.privacyMode && isEdit" class="form-control form-control-sm" disabled value="*****" />
        <input v-else v-model.number="form.lon" type="number" step="any" min="-180" max="180" class="form-control form-control-sm" required :placeholder="$t('node.form.click_map')" />
      </div>
    </div>
    <div v-if="uiStore.privacyMode && !isEdit" class="text-warning" style="font-size:.72rem;margin-top:-4px;margin-bottom:4px">
      {{ $t('node.form.privacy_warning') }}
    </div>

    <div class="row g-2 mb-2">
      <div class="col">
        <label class="form-label small mb-1">{{ $t('node.form.height_agl') }} <span class="text-danger">*</span></label>
        <input v-model.number="form.height_m" type="number" step="0.1" min="0.1" class="form-control form-control-sm" required />
      </div>
      <div class="col">
        <label class="form-label small mb-1">{{ $t('node.form.antenna_gain') }}</label>
        <input
          v-model.number="form.antenna_gain_dbi"
          type="number" step="0.1"
          class="form-control form-control-sm"
          :placeholder="selectedHardware ? `default: ${selectedHardware.default_antenna_gain_dbi}` : 'dBi'"
        />
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">{{ $t('node.form.clutter_env') }}</label>
      <select v-model="form.environment" class="form-select form-select-sm">
        <option value="auto">{{ $t('node.form.clutter_options.auto') }}</option>
        <option value="urban">{{ $t('node.form.clutter_options.urban') }}</option>
        <option value="suburban">{{ $t('node.form.clutter_options.suburban') }}</option>
        <option value="rural">{{ $t('node.form.clutter_options.rural') }}</option>
        <option value="open">{{ $t('node.form.clutter_options.open') }}</option>
      </select>
      <div class="text-muted" style="font-size:.72rem;margin-top:2px">
        {{ $t('node.form.clutter_help') }}
        {{ $t('node.form.clutter_auto_help') }}
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">{{ $t('node.form.lora_preset') }}</label>
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
        {{ $t('node.form.lora_help') }}
      </div>
    </div>

    <div class="mb-2">
      <label class="form-label small mb-1">{{ $t('node.form.sim_radius') }}</label>
      <div class="d-flex align-items-center gap-2">
        <input v-model.number="form.sim_radius_km" type="range" min="1" max="50" step="1" class="form-range flex-fill" />
        <span class="text-muted small" style="width:3rem;text-align:right">{{ form.sim_radius_km }} km</span>
      </div>
      <div class="text-muted" style="font-size:.72rem">{{ $t('node.form.sim_radius_help') }}</div>
    </div>

    <fieldset class="mb-2">
      <legend class="form-label small mb-1 fw-normal">{{ $t('node.status.label') }}</legend>
      <div class="d-flex gap-3">
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="planned" id="s-planned" />
          <label class="form-check-label small" for="s-planned">{{ $t('node.status.planned') }}</label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="deployed" id="s-deployed" />
          <label class="form-check-label small" for="s-deployed">{{ $t('node.status.deployed') }}</label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="radio" v-model="form.status" value="draft" id="s-draft" />
          <label class="form-check-label small" for="s-draft">{{ $t('node.status.draft') }}</label>
        </div>
      </div>
      <div v-if="form.status === 'draft'" class="text-muted" style="font-size:.72rem;margin-top:2px">
        {{ $t('node.status.draft_help') }}
      </div>
    </fieldset>

    <div class="mb-3">
      <label class="form-label small mb-1">{{ $t('node.form.notes') }}</label>
      <textarea v-model="form.notes" class="form-control form-control-sm" rows="2" :placeholder="$t('common.optional')"></textarea>
    </div>

    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary btn-sm flex-fill" :disabled="saving">
        {{ saving ? $t('common.saving') : (isEdit ? $t('common.save_changes') : $t('node.add_node')) }}
      </button>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="emit('cancel')">{{ $t('common.cancel') }}</button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { HardwareProfile, MeshNode, NodeCreate, NodeEnvironment, NodeStatus, NodeUpdate } from '../types'
import { useUIStore } from '../stores/ui'

const { t } = useI18n()
const uiStore = useUIStore()

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
    antenna_gain_dbi: n.antenna_gain_dbi ?? null,
    sim_radius_km: n.sim_radius_km,
    environment: n.environment,
    lora_preset: n.lora_preset,
    status: n.status,
    notes: n.notes ?? null,
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
