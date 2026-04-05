"""
Server-side coordinate fuzzing for public (unauthenticated) API responses.

Uses the same djb2-based algorithm as frontend/src/utils/privacy.ts so
markers appear in the same fuzzed position regardless of which side renders.
"""


def _hash_code(s: str) -> int:
    """Deterministic 32-bit djb2 hash matching the TypeScript implementation."""
    h = 5381
    for c in s:
        # Replicate JS signed 32-bit integer overflow behaviour
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
        # Convert to signed 32-bit (JS `| 0`)
        if h >= 0x80000000:
            h -= 0x100000000
    return h


def fuzz_coords(lat: float, lon: float, node_id: str) -> tuple[float, float]:
    """
    Apply a deterministic ±0.005° offset (~500 m) derived from the node ID.
    The offset is stable for a given ID so markers don't jump around.
    """
    h = _hash_code(node_id)
    # Replicate JS unsigned right-shift (`>>> 16`) — mask to 32-bit first
    h_unsigned = h & 0xFFFFFFFF
    lat_offset = ((h_unsigned & 0xFFFF) / 0xFFFF) * 0.01 - 0.005
    lon_offset = (((h_unsigned >> 16) & 0xFFFF) / 0xFFFF) * 0.01 - 0.005
    return lat + lat_offset, lon + lon_offset
