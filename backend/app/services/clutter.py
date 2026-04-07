"""
Clutter height estimation for SPLAT! -gc parameter.

Two strategies:
  - "auto"     : sample ESA WorldCover 2021 (10 m, public COG on S3) to get a
                 land-cover class, then map it to a realistic obstacle height.
  - manual     : urban / suburban / rural / open → fixed preset heights.

ESA WorldCover tiles are Cloud-Optimised GeoTIFFs hosted on AWS S3 (eu-west-3)
without authentication. GDAL/rasterio fetches only the compressed block that
contains the requested pixel via HTTP range requests, so no full tile is
downloaded.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# ── Manual environment presets ─────────────────────────────────────────────���──

ENVIRONMENT_HEIGHTS: dict[str, float] = {
    "urban":    10.0,   # dense city buildings (~3-4 floors)
    "suburban":  5.0,   # low-rise residential / mixed
    "rural":     2.0,   # scattered structures, hedges
    "open":      0.0,   # fields, water, airport
}

# ── ESA WorldCover 2021 land-cover class → obstacle height (m) ──────────────���
# https://worldcover2021.esa.int/
WORLDCOVER_HEIGHTS: dict[int, float] = {
    10:  8.0,   # Tree cover
    20:  3.0,   # Shrubland
    30:  0.5,   # Grassland
    40:  0.5,   # Cropland
    50: 10.0,   # Built-up
    60:  0.0,   # Bare / sparse vegetation
    70:  0.0,   # Snow and ice
    80:  0.0,   # Permanent water bodies
    90:  1.5,   # Herbaceous wetland
    95:  4.0,   # Mangroves
   100:  0.5,   # Moss and lichen
}

_WORLDCOVER_BUCKET_URL = (
    "https://esa-worldcover.s3.eu-west-3.amazonaws.com/v200/2021/map"
)
# Mirror that doesn't require region-redirect (plain path-style S3 URL)
_WORLDCOVER_BUCKET_URL_ALT = (
    "https://s3.eu-west-3.amazonaws.com/esa-worldcover/v200/2021/map"
)

# Simple in-process cache: (rounded lat, rounded lon) → height
_cache: dict[tuple[float, float], float] = {}
_cache_lock = threading.Lock()


def _tile_name(lat: float, lon: float) -> str:
    """Return the ESA WorldCover tile filename for (lat, lon).

    Tiles are 3° × 3°, named by their SW corner.
    E.g. Pescara (42.45°N, 14.22°E) → N42E012.
    """
    lat_sw = math.floor(lat / 3) * 3
    lon_sw = math.floor(lon / 3) * 3
    ns = "N" if lat_sw >= 0 else "S"
    ew = "E" if lon_sw >= 0 else "W"
    return (
        f"ESA_WorldCover_10m_2021_v200_"
        f"{ns}{abs(lat_sw):02d}{ew}{abs(lon_sw):03d}_Map.tif"
    )


_LC_NAMES = {
    10: "trees", 20: "shrub", 30: "grass", 40: "crop", 50: "built-up",
    60: "bare", 70: "snow", 80: "water", 90: "wetland", 95: "mangrove", 100: "moss",
}

def _sample_worldcover(lat: float, lon: float) -> Optional[float]:
    """
    Fetch the ESA WorldCover land-cover class at (lat, lon) via a COG HTTP
    range request (GDAL VSICURL), then map it to a clutter height.

    Tries the regional S3 URL first; falls back to the path-style URL.
    Returns None if the data cannot be retrieved.
    """
    try:
        import rasterio
        import rasterio.windows

        tile = _tile_name(lat, lon)
        env_opts = {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_CONNECTTIMEOUT": "10",
            "GDAL_HTTP_TIMEOUT": "30",
            "GDAL_HTTP_FOLLOWREDIRECTS": "YES",   # follow S3 regional redirects
        }

        urls = [
            f"/vsicurl/{_WORLDCOVER_BUCKET_URL}/{tile}",
            f"/vsicurl/{_WORLDCOVER_BUCKET_URL_ALT}/{tile}",
        ]

        last_exc: Exception | None = None
        for url in urls:
            try:
                with rasterio.Env(**env_opts):
                    with rasterio.open(url) as ds:
                        row, col = ds.index(lon, lat)
                        if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
                            logger.warning("WorldCover: (%.4f, %.4f) out of tile bounds", lat, lon)
                            return None
                        val = int(ds.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0])

                height = WORLDCOVER_HEIGHTS.get(val, 2.0)
                logger.info(
                    "WorldCover: (%.4f, %.4f) → class %d (%s) → %.1f m clutter",
                    lat, lon, val, _LC_NAMES.get(val, "unknown"), height,
                )
                return height
            except Exception as exc:
                last_exc = exc
                logger.debug("WorldCover URL failed (%s): %s", url, exc)
                continue

        logger.warning("WorldCover lookup failed for (%.4f, %.4f): %s", lat, lon, last_exc)
        return None

    except Exception as exc:
        logger.warning("WorldCover lookup failed for (%.4f, %.4f): %s", lat, lon, exc)
        return None


def resolve_clutter_height(environment: str, lat: float, lon: float) -> float:
    """
    Return the clutter height (metres) to pass to SPLAT!'s -gc flag.

    - 'auto'     → query ESA WorldCover; fall back to 5 m on error
    - any preset → look up in ENVIRONMENT_HEIGHTS
    """
    if environment != "auto":
        return ENVIRONMENT_HEIGHTS.get(environment, 5.0)

    key = (round(lat, 4), round(lon, 4))
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    height = _sample_worldcover(lat, lon)
    result = height if height is not None else 5.0   # suburban as safe default
    with _cache_lock:
        _cache[key] = result
    return result
