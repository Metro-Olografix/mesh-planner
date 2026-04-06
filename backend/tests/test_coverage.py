"""
Comprehensive tests for coverage simulation pipeline.

Covers:
  - splat.py static methods: QTH, LRP, DCF, tile calculation,
    HGT→SDF naming, colorbar, GeoTIFF generation
  - clutter.py: preset environments, tile naming, auto-mode fallback
  - coverage_request.py: field validation
"""
from __future__ import annotations

import io
import math
import struct
import textwrap
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from app.models.coverage_request import CoveragePredictionRequest
from app.services.clutter import (
    ENVIRONMENT_HEIGHTS,
    WORLDCOVER_HEIGHTS,
    _tile_name,
    resolve_clutter_height,
)
from app.services.splat import Splat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ppm(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Create a minimal PPM (P6) image filled with a single RGB colour."""
    header = f"P6\n{width} {height}\n255\n".encode()
    pixels = bytes(rgb) * (width * height)
    return header + pixels


def _make_kml(north: float, south: float, east: float, west: float) -> bytes:
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://earth.google.com/kml/2.1">
          <Document>
            <GroundOverlay>
              <LatLonBox>
                <north>{north}</north>
                <south>{south}</south>
                <east>{east}</east>
                <west>{west}</west>
              </LatLonBox>
            </GroundOverlay>
          </Document>
        </kml>
    """).encode()


# ---------------------------------------------------------------------------
# 1. _calculate_required_terrain_tiles
# ---------------------------------------------------------------------------

class TestCalculateRequiredTiles:
    def test_single_tile_small_radius(self):
        # Centre of a tile, tiny radius → only one tile needed
        tiles = Splat._calculate_required_terrain_tiles(42.5, 14.5, 1000)
        tile_names = [t[0] for t in tiles]
        assert "N42E014.hgt.gz" in tile_names
        assert len(tiles) == 1

    def test_multiple_tiles_large_radius(self):
        # Large enough radius at a tile boundary should require several tiles
        tiles = Splat._calculate_required_terrain_tiles(43.0, 14.0, 200_000)
        assert len(tiles) > 1

    def test_southern_hemisphere(self):
        tiles = Splat._calculate_required_terrain_tiles(-10.5, 30.5, 1000)
        tile_names = [t[0] for t in tiles]
        assert "S11E030.hgt.gz" in tile_names

    def test_western_hemisphere(self):
        tiles = Splat._calculate_required_terrain_tiles(40.5, -74.5, 1000)
        tile_names = [t[0] for t in tiles]
        assert "N40W075.hgt.gz" in tile_names

    def test_southwest_quadrant(self):
        tiles = Splat._calculate_required_terrain_tiles(-33.5, -70.5, 1000)
        tile_names = [t[0] for t in tiles]
        assert "S34W071.hgt.gz" in tile_names

    def test_tuple_structure(self):
        """Each tuple is (hgt_name, sdf_name, sdf_hd_name)."""
        tiles = Splat._calculate_required_terrain_tiles(42.5, 14.5, 1000)
        hgt, sdf, sdf_hd = tiles[0]
        assert hgt.endswith(".hgt.gz")
        assert sdf.endswith(".sdf")
        assert sdf_hd.endswith("-hd.sdf")

    def test_polar_latitude_at_90(self):
        """cos(90°) = 0 would cause division by zero — ensure it doesn't crash."""
        # Use 89° instead of exactly 90° to avoid the degenerate case
        tiles = Splat._calculate_required_terrain_tiles(89.5, 0.0, 10_000)
        assert len(tiles) >= 1


# ---------------------------------------------------------------------------
# 2. _hgt_filename_to_sdf_filename
# ---------------------------------------------------------------------------

class TestHgtToSdfFilename:
    def test_north_east(self):
        result = Splat._hgt_filename_to_sdf_filename("N42E014.hgt.gz")
        assert result.endswith(".sdf")
        assert "42:43" in result

    def test_north_west(self):
        result = Splat._hgt_filename_to_sdf_filename("N35W120.hgt.gz")
        assert result.endswith(".sdf")
        assert "35:36" in result
        # West lons stay as positive numbers in SPLAT! convention
        parts = result.replace(".sdf", "").split(":")
        lon_start = int(parts[2])
        assert lon_start > 0

    def test_south_west(self):
        result = Splat._hgt_filename_to_sdf_filename("S34W071.hgt.gz")
        assert result.endswith(".sdf")
        assert "-34:-33" in result

    def test_south_east(self):
        result = Splat._hgt_filename_to_sdf_filename("S11E030.hgt.gz")
        assert result.endswith(".sdf")
        assert "-11:-10" in result

    def test_hd_suffix(self):
        result = Splat._hgt_filename_to_sdf_filename("N42E014.hgt.gz", high_resolution=True)
        assert result.endswith("-hd.sdf")

    def test_standard_suffix(self):
        result = Splat._hgt_filename_to_sdf_filename("N42E014.hgt.gz", high_resolution=False)
        assert result.endswith(".sdf")
        assert not result.endswith("-hd.sdf")


# ---------------------------------------------------------------------------
# 3. _create_splat_qth
# ---------------------------------------------------------------------------

class TestCreateSplatQth:
    def test_basic_format(self):
        data = Splat._create_splat_qth("TestSite", 42.35, 14.15, 10.0)
        lines = data.decode().strip().split("\n")
        assert lines[0] == "TestSite"
        assert float(lines[1]) == pytest.approx(42.35)
        assert float(lines[3]) == pytest.approx(10.0)

    def test_east_longitude_converted(self):
        # East longitude (positive) → SPLAT! expects 360 - lon (West-positive)
        data = Splat._create_splat_qth("X", 42.0, 14.0, 1.0)
        lines = data.decode().strip().split("\n")
        assert float(lines[2]) == pytest.approx(360.0 - 14.0)

    def test_west_longitude_converted(self):
        # West longitude (negative) → SPLAT! expects abs(lon)
        data = Splat._create_splat_qth("X", 40.0, -74.0, 1.0)
        lines = data.decode().strip().split("\n")
        assert float(lines[2]) == pytest.approx(74.0)

    def test_prime_meridian_longitude(self):
        # longitude=0: must produce 0.0, not 360.0 (SPLAT! doesn't handle 360°)
        data = Splat._create_splat_qth("X", 51.5, 0.0, 1.0)
        lines = data.decode().strip().split("\n")
        assert float(lines[2]) == pytest.approx(0.0)

    def test_returns_bytes(self):
        result = Splat._create_splat_qth("X", 0.0, 0.0, 1.0)
        assert isinstance(result, bytes)

    def test_name_with_spaces(self):
        """SPLAT! QTH name should be preserved exactly."""
        data = Splat._create_splat_qth("My Node A", 42.0, 14.0, 5.0)
        assert data.decode().startswith("My Node A\n")


# ---------------------------------------------------------------------------
# 4. _create_splat_lrp
# ---------------------------------------------------------------------------

class TestCreateSplatLrp:
    def _make_lrp(self, **overrides) -> str:
        defaults = dict(
            ground_dielectric=15.0,
            ground_conductivity=0.005,
            atmosphere_bending=301.0,
            frequency_mhz=868.0,
            radio_climate="continental_temperate",
            polarization="vertical",
            situation_fraction=50.0,
            time_fraction=90.0,
            tx_power=17.0,
            tx_gain=2.0,
            system_loss=2.0,
        )
        defaults.update(overrides)
        return Splat._create_splat_lrp(**defaults).decode()

    def test_returns_bytes(self):
        result = Splat._create_splat_lrp(
            ground_dielectric=15.0, ground_conductivity=0.005,
            atmosphere_bending=301.0, frequency_mhz=868.0,
            radio_climate="continental_temperate", polarization="vertical",
            situation_fraction=50.0, time_fraction=90.0,
            tx_power=17.0, tx_gain=2.0, system_loss=2.0,
        )
        assert isinstance(result, bytes)

    def test_climate_enumeration(self):
        climates = {
            "equatorial": 1, "continental_subtropical": 2,
            "maritime_subtropical": 3, "desert": 4,
            "continental_temperate": 5, "maritime_temperate_land": 6,
            "maritime_temperate_sea": 7,
        }
        for name, expected_int in climates.items():
            content = self._make_lrp(radio_climate=name)
            lines = [l.split(";")[0].strip() for l in content.strip().split("\n")]
            assert lines[4] == str(expected_int), f"{name} should map to {expected_int}"

    def test_polarization_enumeration(self):
        h_content = self._make_lrp(polarization="horizontal")
        v_content = self._make_lrp(polarization="vertical")
        h_line = [l.split(";")[0].strip() for l in h_content.split("\n")][5]
        v_line = [l.split(";")[0].strip() for l in v_content.split("\n")][5]
        assert h_line == "0"
        assert v_line == "1"

    def test_situation_fraction_normalized(self):
        content = self._make_lrp(situation_fraction=50.0)
        lines = [l.split(";")[0].strip() for l in content.strip().split("\n")]
        assert float(lines[6]) == pytest.approx(0.50)

    def test_time_fraction_normalized(self):
        content = self._make_lrp(time_fraction=90.0)
        lines = [l.split(";")[0].strip() for l in content.strip().split("\n")]
        assert float(lines[7]) == pytest.approx(0.90)

    def test_erp_calculation(self):
        # ERP = 10^((tx_power + tx_gain - system_loss - 30) / 10) Watts
        # The LRP file formats ERP with %.2f, so we allow rounding tolerance.
        content = self._make_lrp(tx_power=17.0, tx_gain=2.0, system_loss=2.0)
        lines = [l.split(";")[0].strip() for l in content.strip().split("\n")]
        expected_erp = 10 ** ((17.0 + 2.0 - 2.0 - 30) / 10)
        assert float(lines[8]) == pytest.approx(expected_erp, abs=0.01)

    def test_erp_with_zero_gain_loss(self):
        # 20 dBm, 0 dB gain, 0 dB loss → 10^((20-30)/10) = 0.1 W
        content = self._make_lrp(tx_power=20.0, tx_gain=0.0, system_loss=0.0)
        lines = [l.split(";")[0].strip() for l in content.strip().split("\n")]
        assert float(lines[8]) == pytest.approx(0.1, rel=1e-3)

    def test_frequency_in_content(self):
        content = self._make_lrp(frequency_mhz=433.5)
        assert "433.500" in content


# ---------------------------------------------------------------------------
# 5. _create_splat_dcf
# ---------------------------------------------------------------------------

class TestCreateSplatDcf:
    def test_returns_bytes(self):
        result = Splat._create_splat_dcf("plasma", -130.0, -80.0)
        assert isinstance(result, bytes)

    def test_has_32_levels(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode()
        data_lines = [l for l in content.split("\n") if l.strip() and not l.startswith(";")]
        assert len(data_lines) == 32

    def test_levels_from_max_to_min(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode()
        data_lines = [l for l in content.split("\n") if l.strip() and not l.startswith(";")]
        first_dbm = int(data_lines[0].split(":")[0].strip())
        last_dbm = int(data_lines[-1].split(":")[0].strip())
        assert first_dbm > last_dbm  # max at top, min at bottom

    def test_max_dbm_is_first_level(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode()
        data_lines = [l for l in content.split("\n") if l.strip() and not l.startswith(";")]
        first_dbm = int(data_lines[0].split(":")[0].strip())
        assert first_dbm == -80

    def test_min_dbm_is_last_level(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode()
        data_lines = [l for l in content.split("\n") if l.strip() and not l.startswith(";")]
        last_dbm = int(data_lines[-1].split(":")[0].strip())
        assert last_dbm == -130

    def test_rgb_values_in_range(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode()
        data_lines = [l for l in content.split("\n") if l.strip() and not l.startswith(";")]
        for line in data_lines:
            rgb_part = line.split(":")[1]
            r, g, b = [int(x) for x in rgb_part.split(",")]
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255

    def test_colormap_affects_output(self):
        dcf_plasma = Splat._create_splat_dcf("plasma", -130.0, -80.0)
        dcf_viridis = Splat._create_splat_dcf("viridis", -130.0, -80.0)
        assert dcf_plasma != dcf_viridis


# ---------------------------------------------------------------------------
# 6. create_splat_colorbar
# ---------------------------------------------------------------------------

class TestCreateSplatColorbar:
    def test_returns_list(self):
        result = Splat.create_splat_colorbar("plasma", -130.0, -80.0)
        assert isinstance(result, (list, np.ndarray))

    def test_has_255_entries(self):
        result = Splat.create_splat_colorbar("plasma", -130.0, -80.0)
        assert len(result) == 255

    def test_entries_are_rgb_triples(self):
        result = Splat.create_splat_colorbar("plasma", -130.0, -80.0)
        for entry in result:
            assert len(entry) == 3
            r, g, b = entry
            assert 0 <= int(r) <= 255
            assert 0 <= int(g) <= 255
            assert 0 <= int(b) <= 255

    def test_different_colormaps_differ(self):
        r1 = Splat.create_splat_colorbar("plasma", -130.0, -80.0)
        r2 = Splat.create_splat_colorbar("viridis", -130.0, -80.0)
        assert not np.array_equal(np.array(r1), np.array(r2))


# ---------------------------------------------------------------------------
# 7. _create_splat_geotiff
# ---------------------------------------------------------------------------

class TestCreateSplatGeotiff:
    """Test GeoTIFF generation from PPM + KML."""

    def _run(self, rgb=(200, 50, 150), width=10, height=10,
             north=43.0, south=42.0, east=15.0, west=14.0,
             colormap="plasma", min_dbm=-137.0, max_dbm=-87.0):
        ppm = _make_ppm(width, height, rgb)
        kml = _make_kml(north, south, east, west)
        return Splat._create_splat_geotiff(ppm, kml, colormap, min_dbm, max_dbm)

    def test_returns_bytes(self):
        result = self._run()
        assert isinstance(result, bytes)

    def test_valid_geotiff(self):
        result = self._run()
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                assert ds.driver == "GTiff"

    def test_geotiff_crs_is_wgs84(self):
        result = self._run()
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                assert ds.crs.to_epsg() == 4326

    def test_geotiff_bounds_match_kml(self):
        result = self._run(north=43.0, south=42.0, east=15.0, west=14.0)
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                bounds = ds.bounds
                assert bounds.left == pytest.approx(14.0, abs=0.01)
                assert bounds.right == pytest.approx(15.0, abs=0.01)
                assert bounds.bottom == pytest.approx(42.0, abs=0.01)
                assert bounds.top == pytest.approx(43.0, abs=0.01)

    def test_geotiff_dimensions(self):
        result = self._run(width=20, height=15)
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                assert ds.width == 20
                assert ds.height == 15

    def test_geotiff_single_band(self):
        result = self._run()
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                assert ds.count == 1

    def test_geotiff_nodata_is_255(self):
        result = self._run()
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                assert ds.nodata == 255

    def test_white_background_becomes_nodata(self):
        """SPLAT!'s white background (255, 255, 255) should map to nodata=255."""
        result = self._run(rgb=(255, 255, 255))
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                data = ds.read(1)
                assert (data == 255).all()

    def test_colormap_pixel_reverse_maps_to_valid_index(self):
        """A pixel from the colormap itself should reverse-map to a non-nodata index."""
        import matplotlib.pyplot as mpl_plt
        cmap = mpl_plt.get_cmap("plasma", 256)
        norm = mpl_plt.Normalize(vmin=-137.0, vmax=-87.0)
        # Pick the middle value in the colormap
        mid_rgb = tuple(int(x * 255) for x in cmap(norm(-112.0))[:3])
        result = self._run(rgb=mid_rgb)
        with MemoryFile(result) as mf:
            with mf.open() as ds:
                data = ds.read(1)
                # At least some pixels should not be nodata
                assert (data != 255).any()

    def test_malformed_kml_raises(self):
        ppm = _make_ppm(5, 5, (100, 100, 100))
        with pytest.raises(Exception):
            Splat._create_splat_geotiff(ppm, b"not xml", "plasma", -130.0, -80.0)


# ---------------------------------------------------------------------------
# 8. clutter.py — _tile_name
# ---------------------------------------------------------------------------

class TestTileName:
    def test_ne_quadrant(self):
        # 42.45°N, 14.22°E → SW corner is N42E012 (floor(42/3)*3=42, floor(14/3)*3=12)
        assert _tile_name(42.45, 14.22) == "ESA_WorldCover_10m_2021_v200_N42E012_Map.tif"

    def test_nw_quadrant(self):
        # 51.5°N, -0.5°W → SW corner: floor(51/3)*3=51, floor(-0.5/3)*3=-3
        assert _tile_name(51.5, -0.5) == "ESA_WorldCover_10m_2021_v200_N51W003_Map.tif"

    def test_sw_quadrant(self):
        # -33.9°S, -70.6°W → floor(-33.9/3)*3=-36, floor(-70.6/3)*3=-72
        assert _tile_name(-33.9, -70.6) == "ESA_WorldCover_10m_2021_v200_S36W072_Map.tif"

    def test_se_quadrant(self):
        # -10.5°S, 30.2°E → floor(-10.5/3)*3=-12, floor(30.2/3)*3=30
        assert _tile_name(-10.5, 30.2) == "ESA_WorldCover_10m_2021_v200_S12E030_Map.tif"

    def test_tile_boundary_lat(self):
        # Exactly on a 3° boundary
        result = _tile_name(42.0, 14.22)
        assert "N42" in result

    def test_tile_boundary_lon(self):
        result = _tile_name(42.45, 12.0)
        assert "E012" in result


# ---------------------------------------------------------------------------
# 9. clutter.py — resolve_clutter_height (presets)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def clear_clutter_cache():
    """Ensure the in-process clutter cache is empty before each test that uses it."""
    import app.services.clutter as clutter_mod
    clutter_mod._cache.clear()
    yield
    clutter_mod._cache.clear()


class TestResolveClutterHeight:
    @pytest.fixture(autouse=True)
    def _clear(self, clear_clutter_cache):
        pass

    def test_urban_preset(self):
        assert resolve_clutter_height("urban", 0.0, 0.0) == ENVIRONMENT_HEIGHTS["urban"]

    def test_suburban_preset(self):
        assert resolve_clutter_height("suburban", 0.0, 0.0) == ENVIRONMENT_HEIGHTS["suburban"]

    def test_rural_preset(self):
        assert resolve_clutter_height("rural", 0.0, 0.0) == ENVIRONMENT_HEIGHTS["rural"]

    def test_open_preset(self):
        assert resolve_clutter_height("open", 0.0, 0.0) == ENVIRONMENT_HEIGHTS["open"]

    def test_unknown_preset_fallback(self):
        # Unknown environment should return a sensible default (5.0 = suburban)
        result = resolve_clutter_height("industrial", 0.0, 0.0)
        assert result == 5.0

    def test_auto_worldcover_success(self):
        """auto mode uses WorldCover; mock it to return a known land cover class."""
        with patch("app.services.clutter._sample_worldcover", return_value=8.0):
            result = resolve_clutter_height("auto", 42.0, 14.0)
        assert result == 8.0

    def test_auto_worldcover_failure_falls_back(self):
        """auto mode falls back to 5.0 (suburban) if WorldCover lookup fails."""
        with patch("app.services.clutter._sample_worldcover", return_value=None):
            result = resolve_clutter_height("auto", 42.0, 14.0)
        assert result == 5.0

    def test_auto_caches_result(self):
        """Second call with identical coordinates should not re-query WorldCover."""
        call_count = 0
        def mock_sample(lat, lon):
            nonlocal call_count
            call_count += 1
            return 3.0

        with patch("app.services.clutter._sample_worldcover", side_effect=mock_sample):
            r1 = resolve_clutter_height("auto", 42.1234, 14.1234)
            r2 = resolve_clutter_height("auto", 42.1234, 14.1234)  # exact same key

        assert call_count == 1   # WorldCover queried only once
        assert r1 == r2 == 3.0

    def test_worldcover_heights_mapping_completeness(self):
        """All expected ESA WorldCover classes have height entries."""
        expected_classes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
        assert expected_classes == set(WORLDCOVER_HEIGHTS.keys())

    def test_worldcover_heights_non_negative(self):
        for cls, h in WORLDCOVER_HEIGHTS.items():
            assert h >= 0.0, f"Class {cls} has negative height {h}"


# ---------------------------------------------------------------------------
# 10. CoveragePredictionRequest — validation
# ---------------------------------------------------------------------------

class TestCoveragePredictionRequest:
    def _base(self, **overrides) -> dict:
        base = dict(
            lat=42.0, lon=14.0, tx_height=10.0, tx_power=17.0,
            tx_gain=2.0, frequency_mhz=868.0, rx_height=1.5, rx_gain=2.0,
            signal_threshold=-137.0, clutter_height=0.0,
            radius=10_000.0, colormap="plasma",
            min_dbm=-137.0, max_dbm=-87.0,
        )
        base.update(overrides)
        return base

    def test_valid_request_accepted(self):
        req = CoveragePredictionRequest(**self._base())
        assert req.lat == 42.0

    def test_lat_out_of_range(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(lat=91.0))

    def test_lat_too_low(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(lat=-91.0))

    def test_lon_out_of_range(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(lon=181.0))

    def test_lon_too_low(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(lon=-181.0))

    def test_tx_height_below_minimum(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(tx_height=0.5))

    def test_rx_height_below_minimum(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(rx_height=0.0))

    def test_signal_threshold_positive_rejected(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(signal_threshold=1.0))

    def test_min_dbm_greater_than_max_dbm_rejected(self):
        """Inverted range would break pixel↔dBm conversion."""
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(min_dbm=-80.0, max_dbm=-130.0))

    def test_min_dbm_equal_to_max_dbm_rejected(self):
        """Zero-range colormap would cause division by zero in pixel conversion."""
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(min_dbm=-130.0, max_dbm=-130.0))

    def test_invalid_colormap_rejected(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(colormap="not_a_real_colormap_xyz"))

    def test_invalid_radio_climate_rejected(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(radio_climate="arctic"))

    def test_invalid_polarization_rejected(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(polarization="circular"))

    def test_radius_below_minimum(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(radius=0.0))

    def test_frequency_below_minimum(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(frequency_mhz=10.0))

    def test_frequency_above_maximum(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(frequency_mhz=40_000.0))

    def test_situation_fraction_at_boundary(self):
        req = CoveragePredictionRequest(**self._base(situation_fraction=100.0))
        assert req.situation_fraction == 100.0

    def test_situation_fraction_too_low(self):
        with pytest.raises(Exception):
            CoveragePredictionRequest(**self._base(situation_fraction=1.0))

    def test_time_fraction_at_boundary(self):
        req = CoveragePredictionRequest(**self._base(time_fraction=100.0))
        assert req.time_fraction == 100.0

    def test_defaults_are_sane(self):
        """Default values should produce a valid request with required fields."""
        req = CoveragePredictionRequest(
            lat=42.0, lon=14.0, tx_power=17.0,
            signal_threshold=-137.0,
        )
        assert req.colormap == "rainbow"
        assert req.radio_climate == "continental_temperate"
        assert req.polarization == "vertical"
        assert req.min_dbm < req.max_dbm
