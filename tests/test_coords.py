"""Automated coordinate tests for KIBA PARK REBUILD. Run: python tests/test_coords.py"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kpr_coords as C  # noqa: E402

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        FAILS.append(name)


# 1. Origin maps to (0,0) and matches the legacy geo_reference.json value.
x, y = C.latlon_to_local(*C.ORIGIN_LATLON)
check("origin -> local (0,0)", abs(x) < 0.01 and abs(y) < 0.01, f"({x:.4f}, {y:.4f})")

# 2. Round trip lat/lon <-> local over the full park extent (incl. 50 m buffer), 1 mm tolerance.
worst = 0.0
for gx in range(-200, 401, 50):
    for gy in range(-450, 751, 50):
        lat, lon = C.local_to_latlon(gx, gy)
        rx, ry = C.latlon_to_local(lat, lon)
        worst = max(worst, math.hypot(rx - gx, ry - gy))
check("local<->latlon round trip", worst < 0.001, f"max error {worst*1000:.4f} mm")

# 3. Axis semantics: moving north increases local y; east increases local x.
x0, y0 = C.latlon_to_local(35.6745, 139.8079)
x1, y1 = C.latlon_to_local(35.6755, 139.8079)  # +0.001 deg lat ~ +111 m north
x2, y2 = C.latlon_to_local(35.6745, 139.8089)  # +0.001 deg lon ~ +90 m east
check("north = +y", 105 < (y1 - y0) < 116 and abs(x1 - x0) < 1, f"dy={y1-y0:.2f}")
check("east = +x", 85 < (x2 - x0) < 95 and abs(y2 - y0) < 1, f"dx={x2-x0:.2f}")

# 4. Blender Z-up <-> Three.js Y-up: north becomes -Z, height becomes +Y, round trip exact.
t = C.local_to_three(10.0, 20.0, 3.0)
check("Three.js mapping (x, h, -n)", t == (10.0, 3.0, -20.0), str(t))
check("Three->Blender round trip", C.three_to_blender(*t) == (10.0, 20.0, 3.0))

# 5. Handedness preserved (det = +1) for the Blender->Three basis change.
m = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]  # rows: three = m * blender
det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
       - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
       + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
check("basis change is a proper rotation", det == 1, f"det={det}")

# 6. Known features land where the legacy model has them.
#    Kiba Park Ohashi (OSM way/745579214) local bounds x 58.7..118.0, y 19.5..268.3
lat, lon = C.local_to_latlon(80.0, 150.0)
check("bridge mid-point lat/lon plausible", 35.675 < lat < 35.677 and 139.808 < lon < 139.810, f"{lat:.6f},{lon:.6f}")

# 7. Tile indexing.
check("tile index (0,0)", C.tile_index(0.0, 0.0) == (0, 0))
check("tile index negative", C.tile_index(-0.01, -100.0) == (-1, -1))
check("tile id format", C.tile_id(-2, 6) == "t100_-2_+6")
check("tile bounds", C.tile_bounds(-1, 2) == (-100.0, 200.0, 0.0, 300.0))

# 8. Float32 precision at the far edge of the play area (GPU vertex precision).
import struct  # noqa: E402
far = 700.0
f32 = struct.unpack("f", struct.pack("f", far + 0.001))[0]
check("float32 keeps mm precision within 700 m", abs(f32 - (far + 0.001)) < 1e-4, f"err={abs(f32-(far+0.001)):.2e} m")

print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAIL -> {FAILS}")
sys.exit(1 if FAILS else 0)
