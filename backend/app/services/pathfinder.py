"""
Pathfinder service: max-min bottleneck SNR path over the mesh node graph.

Algorithm: modified Dijkstra that maximises the minimum-SNR hop (bottleneck).
When SPLAT! coverage data is available for a transmitter, the terrain-attenuated
signal level from the GeoTIFF raster is used for edge SNR.  Links are validated
bidirectionally — both TX→RX and RX→TX must have coverage.  When no SPLAT! data
exists, Friis free-space is used with a penalty to prefer terrain-validated hops.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import List, Optional

from rasterio.io import MemoryFile

# ── Meshtastic EU_868 modem presets ─────────────────────────────────────────
# Each entry: (spreading_factor, bandwidth_hz, receiver_noise_figure_db)
# Bandwidth determines the thermal noise floor; SF determines demodulation
# sensitivity (already encoded in hw.rx_sensitivity_dbm, so NF is kept fixed).
_LORA_NF_DB = 6.0   # SX1262 typical receiver noise figure

LORA_PRESETS: dict[str, dict] = {
    "SHORT_FAST":      {"sf": 7,  "bw_hz": 500_000},
    "SHORT_SLOW":      {"sf": 8,  "bw_hz": 250_000},
    "MEDIUM_FAST":     {"sf": 9,  "bw_hz": 250_000},
    "MEDIUM_SLOW":     {"sf": 10, "bw_hz": 250_000},
    "LONG_FAST":       {"sf": 11, "bw_hz": 250_000},
    "LONG_SLOW":       {"sf": 12, "bw_hz": 125_000},
    "VERY_LONG_SLOW":  {"sf": 12, "bw_hz": 125_000},
}
_DEFAULT_PRESET = "MEDIUM_FAST"


def noise_floor_dbm(lora_preset: str = _DEFAULT_PRESET) -> float:
    """Thermal noise floor + receiver noise figure in dBm for the given preset."""
    bw_hz = LORA_PRESETS.get(lora_preset, LORA_PRESETS[_DEFAULT_PRESET])["bw_hz"]
    return -174.0 + 10.0 * math.log10(bw_hz) + _LORA_NF_DB


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def friis_rx_dbm(
    tx_dbm: float,
    tx_gain_dbi: float,
    rx_gain_dbi: float,
    freq_mhz: float,
    dist_m: float,
    system_loss_db: float = 2.0,
) -> float:
    """Friis free-space received power in dBm."""
    dist_m = max(dist_m, 1.0)
    fspl = 20.0 * math.log10(dist_m) + 20.0 * math.log10(freq_mhz * 1e6) - 147.55
    return tx_dbm + tx_gain_dbi + rx_gain_dbi - fspl - system_loss_db


def _splat_read_pixel(geotiff_bytes: bytes, lat: float, lon: float) -> Optional[int]:
    """
    Read the raw pixel value from a SPLAT! coverage GeoTIFF at (lat, lon).

    Returns the pixel value (0–254) on success, or None if the location is
    outside the raster, nodata, or on any read error.
    """
    try:
        import rasterio.windows
        with MemoryFile(geotiff_bytes) as mf:
            with mf.open() as ds:
                row, col = ds.index(lon, lat)
                if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
                    return None
                val = int(ds.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0])
                if val == ds.nodata or val == 255:
                    return None
                return val
    except Exception:
        return None


def _splat_pixel_to_dbm(pixel: int, rx_sensitivity_dbm: float) -> float:
    """
    Convert a SPLAT! GeoTIFF pixel value (0–254) to received power in dBm.

    Coverage is generated with min_dbm = rx_sensitivity and
    max_dbm = rx_sensitivity + 50, mapping linearly to pixels 0–254.
    """
    min_dbm = rx_sensitivity_dbm
    max_dbm = rx_sensitivity_dbm + 50.0
    return min_dbm + (pixel / 254.0) * (max_dbm - min_dbm)


@dataclass
class GraphNode:
    idx: int
    node_id: Optional[object]   # UUID or None for virtual endpoints
    name: str
    lat: float
    lon: float
    tx_dbm: float
    tx_gain_dbi: float
    rx_sensitivity_dbm: float
    freq_mhz: float
    lora_preset: str = _DEFAULT_PRESET


# Penalty applied to Friis-only links (no SPLAT! terrain validation).
# This makes the pathfinder prefer SPLAT!-validated hops over optimistic
# free-space estimates that ignore terrain obstructions.
_FRIIS_ONLY_PENALTY_DB = 15.0


def build_snr_matrix(
    graph_nodes: List[GraphNode],
    coverage_data: dict,   # {str(node_id): geotiff_bytes}
) -> List[List[Optional[float]]]:
    """
    Build an n×n SNR matrix.

    Edge (i→j) exists when:
      - Friis received power at j exceeds j's sensitivity threshold, AND
      - If SPLAT! data is available for i, j's position must fall within i's
        coverage raster (terrain-aware check), AND
      - **Bidirectional**: if SPLAT! data is available for j, i's position must
        also fall within j's coverage raster.

    Edge weight (SNR in dB):
      - When SPLAT! data exists for i: derived from the SPLAT! raster pixel
        (terrain-attenuated received power), not Friis.
      - Otherwise: Friis free-space SNR minus a penalty to discourage
        unvalidated links.
    """
    n = len(graph_nodes)
    matrix: List[List[Optional[float]]] = [[None] * n for _ in range(n)]

    for i, tx in enumerate(graph_nodes):
        tx_cov = coverage_data.get(str(tx.node_id)) if tx.node_id else None
        for j, rx in enumerate(graph_nodes):
            if i == j:
                continue
            dist = haversine_m(tx.lat, tx.lon, rx.lat, rx.lon)
            friis_rx = friis_rx_dbm(tx.tx_dbm, tx.tx_gain_dbi, rx.tx_gain_dbi, tx.freq_mhz, dist)

            if friis_rx <= rx.rx_sensitivity_dbm:
                continue   # link too weak even in free space

            # ── Fix 2: Bidirectional SPLAT! validation ────────────────────
            # If SPLAT! data exists for the TX node, the RX location must
            # fall within coverage.  Additionally, if SPLAT! data exists for
            # the RX node (acting as TX on the return path), the TX location
            # must also fall within *that* coverage — otherwise the reverse
            # direction is blocked and the link is unusable for mesh comms.
            rx_cov = coverage_data.get(str(rx.node_id)) if rx.node_id else None

            tx_pixel: Optional[int] = None
            if tx_cov:
                tx_pixel = _splat_read_pixel(tx_cov, rx.lat, rx.lon)
                if tx_pixel is None:
                    continue   # TX coverage says RX location is unreachable

            if rx_cov:
                reverse_pixel = _splat_read_pixel(rx_cov, tx.lat, tx.lon)
                if reverse_pixel is None:
                    continue   # reverse direction blocked by terrain

            # ── Fix 1: Use SPLAT! dBm for SNR when available ─────────────
            nf = noise_floor_dbm(rx.lora_preset)
            if tx_pixel is not None:
                splat_rx_dbm = _splat_pixel_to_dbm(tx_pixel, rx.rx_sensitivity_dbm)
                snr = splat_rx_dbm - nf
            else:
                # ── Fix 3: Penalize Friis-only (unvalidated) links ───────
                snr = friis_rx - nf - _FRIIS_ONLY_PENALTY_DB

            matrix[i][j] = round(snr, 2)

    return matrix


def find_max_min_snr_path(
    graph_nodes: List[GraphNode],
    snr_matrix: List[List[Optional[float]]],
    src_idx: int,
    dst_idx: int,
) -> tuple[Optional[List[int]], Optional[float]]:
    """
    Find the path whose worst hop has the best SNR (max-min bottleneck).

    Returns (path_as_index_list, bottleneck_snr_db) or (None, None) if unreachable.
    """
    n = len(graph_nodes)
    best = [-math.inf] * n
    best[src_idx] = math.inf
    prev = [-1] * n

    # max-heap via negation
    heap: list = [(-math.inf, src_idx)]

    while heap:
        neg_snr, u = heapq.heappop(heap)
        curr = -neg_snr
        if curr < best[u]:
            continue
        for v in range(n):
            edge = snr_matrix[u][v]
            if edge is None:
                continue
            path_snr = min(curr, edge)
            if path_snr > best[v]:
                best[v] = path_snr
                prev[v] = u
                heapq.heappush(heap, (-path_snr, v))

    if best[dst_idx] == -math.inf:
        return None, None

    path: List[int] = []
    cur = dst_idx
    while cur != -1:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path, best[dst_idx]
