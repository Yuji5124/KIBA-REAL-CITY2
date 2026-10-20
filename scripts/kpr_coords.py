"""KIBA PARK REBUILD - shared coordinate definitions (single source of truth).

GIS   : EPSG:6677 (JGD2011 / Japan Plane Rectangular CS IX), metres, X=east(easting) Y=north(northing)
Local : origin = legacy KIBA-REAL-CITY origin (kept for comparison with v01-v07)
        local_e = E - ORIGIN_E, local_n = N - ORIGIN_N, h = T.P. elevation (m)
Blender (Z-up, right-handed) : (x, y, z) = (local_e, local_n, h)
glTF / Three.js (Y-up, right-handed): (x, y, z) = (local_e, h, -local_n)
  -> this is exactly what the Blender glTF exporter's default "+Y up" conversion produces.
"""
from __future__ import annotations

import math

from pyproj import Transformer

CRS_PROJECTED = "EPSG:6677"
CRS_GEOGRAPHIC = "EPSG:6668"  # JGD2011 geographic (lat/lon). WGS84 differs by < ~0.1 m here.
ORIGIN_E = -2302.317826321731
ORIGIN_N = -36106.717222697174
ORIGIN_LATLON = (35.67455, 139.8079)
VERTICAL_DATUM = "T.P. (Tokyo Peil) orthometric height, metres (GSI DEM / PLATEAU)"
TILE_SIZE_M = 100.0

_to_proj = Transformer.from_crs(CRS_GEOGRAPHIC, CRS_PROJECTED, always_xy=True)
_to_geo = Transformer.from_crs(CRS_PROJECTED, CRS_GEOGRAPHIC, always_xy=True)


def latlon_to_local(lat: float, lon: float) -> tuple[float, float]:
    e, n = _to_proj.transform(lon, lat)
    return e - ORIGIN_E, n - ORIGIN_N


def local_to_latlon(x: float, y: float) -> tuple[float, float]:
    lon, lat = _to_geo.transform(x + ORIGIN_E, y + ORIGIN_N)
    return lat, lon


def local_to_blender(x: float, y: float, h: float) -> tuple[float, float, float]:
    return (x, y, h)


def blender_to_three(bx: float, by: float, bz: float) -> tuple[float, float, float]:
    return (bx, bz, -by)


def three_to_blender(tx: float, ty: float, tz: float) -> tuple[float, float, float]:
    return (tx, -tz, ty)


def local_to_three(x: float, y: float, h: float) -> tuple[float, float, float]:
    return blender_to_three(*local_to_blender(x, y, h))


def tile_index(x: float, y: float, size: float = TILE_SIZE_M) -> tuple[int, int]:
    return math.floor(x / size), math.floor(y / size)


def tile_id(i: int, j: int, size: float = TILE_SIZE_M) -> str:
    return f"t{int(size)}_{i:+d}_{j:+d}"


def tile_bounds(i: int, j: int, size: float = TILE_SIZE_M) -> tuple[float, float, float, float]:
    return (i * size, j * size, (i + 1) * size, (j + 1) * size)
