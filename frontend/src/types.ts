export type NodeStatus = 'planned' | 'deployed' | 'draft'

export interface HardwareProfile {
  id: string
  name: string
  manufacturer: string
  tx_power_dbm: number
  frequency_mhz: number
  rx_sensitivity_dbm: number
  default_antenna_gain_dbi: number
  description: string | null
}

export type NodeEnvironment = 'auto' | 'urban' | 'suburban' | 'rural' | 'open'

export type LoraPreset =
  | 'SHORT_FAST' | 'SHORT_SLOW'
  | 'MEDIUM_FAST' | 'MEDIUM_SLOW'
  | 'LONG_FAST' | 'LONG_SLOW'
  | 'VERY_LONG_SLOW'

export interface MeshNode {
  id: string
  name: string
  lat: number
  lon: number
  height_m: number
  status: NodeStatus
  hardware_id: string
  antenna_gain_dbi?: number | null
  sim_radius_km: number
  environment: NodeEnvironment
  lora_preset: LoraPreset
  notes?: string | null
  created_by?: string
  created_at?: string
  updated_at?: string
  hardware: HardwareProfile
  coverage_status: string | null
}

export interface NodeCreate {
  name: string
  lat: number
  lon: number
  height_m: number
  status: NodeStatus
  hardware_id: string
  antenna_gain_dbi?: number | null
  sim_radius_km: number
  environment: NodeEnvironment
  lora_preset: LoraPreset
  notes?: string | null
}

export interface NodeUpdate {
  name?: string
  lat?: number
  lon?: number
  height_m?: number
  status?: NodeStatus
  hardware_id?: string
  antenna_gain_dbi?: number | null
  sim_radius_km?: number
  environment?: NodeEnvironment
  lora_preset?: LoraPreset
  notes?: string | null
}

export interface HopInfo {
  node_id: string | null
  name: string
  lat: number
  lon: number
  snr_db: number | null
}

export interface PathResult {
  found: boolean
  hops: HopInfo[]
  bottleneck_snr_db: number | null
  total_relay_hops: number
  message: string
}

export interface ActivityEvent {
  type: 'node_created' | 'node_updated' | 'node_deleted'
  data: {
    id: string
    name: string
    by: string
  }
  timestamp: Date
}

export type ToastType = 'success' | 'warning' | 'danger' | 'info'

export interface Toast {
  id: number
  message: string
  type: ToastType
}

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface CoverageJob {
  nodeId: string
  nodeName: string
  status: JobStatus
  startedAt: Date
  finishedAt: Date | null
}
