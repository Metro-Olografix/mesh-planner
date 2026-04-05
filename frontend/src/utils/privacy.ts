/** Deterministic 32-bit hash (djb2). */
function hashCode(str: string): number {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) | 0
  }
  return hash
}

/**
 * Apply a deterministic random offset to coordinates (~500 m).
 * The offset is stable for a given id so markers don't jump around.
 */
export function fuzzCoords(lat: number, lon: number, id: string): { lat: number; lon: number } {
  const h = hashCode(id)
  // Two independent seeds from the same hash
  const latOffset = ((h & 0xffff) / 0xffff) * 0.01 - 0.005        // [-0.005, +0.005]
  const lonOffset = (((h >>> 16) & 0xffff) / 0xffff) * 0.01 - 0.005
  return { lat: lat + latOffset, lon: lon + lonOffset }
}

/** Format a coordinate value — masked when privacy mode is on. */
export function formatCoord(value: number, privacyOn: boolean): string {
  return privacyOn ? '*****' : value.toFixed(5)
}
