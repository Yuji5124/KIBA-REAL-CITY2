"""KIBA PARK REBUILD - Phase 0: tile-plan verification (read-only).

Reads the existing KIBA-REAL-CITY OSM extract (never modifies it), rebuilds the
Kiba Park multipolygon (OSM relation/14273608) in EPSG:6677 local metres with the
existing shared origin, and evaluates 50 m / 100 m / 200 m tile grids.

Usage:
    python scripts/phase0_tile_plan.py <path-to-KIBA-REAL-CITY-main> [out.json]
Requires: pyproj, shapely
"""
from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

ORIGIN = (-2302.317826321731, -36106.717222697174)  # EPSG:6677, from output/geo_reference*.json
PARK_RELATION = "14273608"
PARK_OUTER_WAYS = ("845051277", "845051292", "845051284")
BUFFER_M = 50.0  # play/visual margin around the park boundary


def load_park(osm_path: Path):
    root = ET.parse(osm_path).getroot()
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    ways = {w.get("id"): [nd.get("ref") for nd in w.iter("nd")] for w in root.iter("way")}
    to_6677 = Transformer.from_crs(4326, 6677, always_xy=True)
    lines = []
    for wid in PARK_OUTER_WAYS:
        pts = [to_6677.transform(*nodes[n]) for n in ways[wid]]
        lines.append(LineString([(x - ORIGIN[0], y - ORIGIN[1]) for x, y in pts]))
    return unary_union(list(polygonize(unary_union(lines))))


def tiles_for(region, size: float):
    minx, miny, maxx, maxy = region.bounds
    i0, i1 = math.floor(minx / size), math.ceil(maxx / size)
    j0, j1 = math.floor(miny / size), math.ceil(maxy / size)
    out = []
    for j in range(j0, j1):
        for i in range(i0, i1):
            t = box(i * size, j * size, (i + 1) * size, (j + 1) * size)
            if t.intersects(region):
                out.append((i, j, t))
    return out


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tile_plan.json")
    park = load_park(src / "data/raw/kiba_osm_phase2a.osm")
    region = park.buffer(BUFFER_M)
    legacy_square = box(-250, -250, 250, 250)
    result = {
        "crs": "EPSG:6677",
        "origin_projected_m": list(ORIGIN),
        "park_relation": f"relation/{PARK_RELATION}",
        "park_area_m2_osm": round(park.area, 1),
        "park_bounds_local_m": [round(v, 2) for v in park.bounds],
        "park_area_inside_legacy_500m_square_m2": round(park.intersection(legacy_square).area, 1),
        "buffer_m": BUFFER_M,
        "region_bounds_local_m": [round(v, 2) for v in region.bounds],
        "grids": {},
    }
    for size in (50.0, 100.0, 200.0):
        tiles = tiles_for(region, size)
        verts_1m = (int(size / 1) + 1) ** 2
        verts_2m = (int(size / 2) + 1) ** 2
        result["grids"][str(int(size))] = {
            "tile_count": len(tiles),
            "tiles_touching_park": sum(1 for *_, t in tiles if t.intersects(park)),
            "per_tile_tris_at_1m": 2 * int(size) ** 2,
            "per_tile_tris_at_2m": 2 * int(size / 2) ** 2,
            "per_tile_verts_at_1m": verts_1m,
            "per_tile_verts_at_2m": verts_2m,
            "total_tris_at_2m": len(tiles) * 2 * int(size / 2) ** 2,
            "tiles": [
                {"id": f"t{int(size)}_{i:+d}_{j:+d}", "i": i, "j": j,
                 "bounds_local_m": [round(v, 1) for v in t.bounds],
                 "park_fraction": round(t.intersection(park).area / t.area, 3)}
                for i, j, t in tiles
            ] if size == 100.0 else None,
        }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {k: v for k, v in result.items() if k != "grids"}
    summary["grids"] = {k: {kk: vv for kk, vv in g.items() if kk != "tiles"} for k, g in result["grids"].items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
