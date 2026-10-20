"""KIBA PARK REBUILD - coverage map: legacy 500 m data vs full park (read-only).

Usage: python scripts/phase0_coverage_map.py <KIBA-REAL-CITY-main> <out.png> [out.json]
Draws (local EPSG:6677 metres): legacy 500 m square (= extent of legacy OSM
features and GSI terrain), Kiba Park boundary (OSM relation/14273608), park part
outside the legacy square, legacy DEM1A tile cache footprint, 55 planned 100 m
tiles coloured by legacy coverage, Kiba Park Ohashi (OSM footprint + G6.2 pylon).
"""
from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from shapely.geometry import LineString, Polygon, box  # noqa: E402
from shapely.ops import polygonize, unary_union  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kpr_coords as C  # noqa: E402

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f or "msgothic" in f.lower() or "YuGoth" in f:
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
        break

LEGACY = box(-250, -250, 250, 250)
DEM1A_CACHED = [(116437 + i, 51615 + j) for i in range(3) for j in range(3)]


def tile_poly_z17(x: int, y: int) -> Polygon:
    def lonlat(px, py):
        n = 1 << 17
        lon = px / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * py / n))))
        return C.latlon_to_local(lat, lon)
    return Polygon([lonlat(x, y), lonlat(x + 1, y), lonlat(x + 1, y + 1), lonlat(x, y + 1)])


def main() -> None:
    legacy_root, out_png = Path(sys.argv[1]), Path(sys.argv[2])
    out_json = Path(sys.argv[3]) if len(sys.argv) > 3 else out_png.with_suffix(".json")
    root = ET.parse(legacy_root / "data/raw/kiba_osm_phase2a.osm").getroot()
    nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node")}
    ways = {}
    for w in root.iter("way"):
        ways[w.get("id")] = ([nd.get("ref") for nd in w.iter("nd")], {t.get("k"): t.get("v") for t in w.iter("tag")})

    def local(ids):
        return [C.latlon_to_local(*nodes[i]) for i in ids if i in nodes]

    park = unary_union(list(polygonize(unary_union(
        [LineString(local(ways[w][0])) for w in ("845051277", "845051292", "845051284")]))))
    outside = park.difference(LEGACY)
    bridge = Polygon(local(ways["745579214"][0]))
    dem_cached = unary_union([tile_poly_z17(x, y) for x, y in DEM1A_CACHED])
    region = park.buffer(50)
    tiles = []
    for j in range(math.floor(region.bounds[1] / 100), math.ceil(region.bounds[3] / 100)):
        for i in range(math.floor(region.bounds[0] / 100), math.ceil(region.bounds[2] / 100)):
            t = box(*C.tile_bounds(i, j))
            if t.intersects(region):
                tiles.append((i, j, t, t.intersection(LEGACY).area / t.area))

    fig, ax = plt.subplots(figsize=(9, 15), dpi=130)
    ax.set_facecolor("#f4f2ec")
    colors = {"full": "#9cc59a", "part": "#f2d27a", "none": "#e8a49c"}
    for i, j, t, frac in tiles:
        key = "full" if frac > 0.999 else ("part" if frac > 0 else "none")
        x, y = t.exterior.xy
        ax.fill(x, y, color=colors[key], alpha=0.55, lw=0)
        ax.plot(x, y, color="#ffffff", lw=0.8)
        ax.text(t.centroid.x, t.centroid.y + 30, f"{i:+d},{j:+d}", ha="center", va="center", fontsize=6, color="#555")
    for wid, (ids, tags) in ways.items():
        pts = local(ids)
        if len(pts) < 2:
            continue
        xs, ys = zip(*pts)
        if tags.get("natural") == "water" or "waterway" in tags:
            ax.plot(xs, ys, color="#4a90c2", lw=1.0, alpha=0.8)
        elif tags.get("highway") in ("footway", "path", "pedestrian", "steps"):
            ax.plot(xs, ys, color="#8a6d3b", lw=0.5, alpha=0.7)
        elif "highway" in tags:
            ax.plot(xs, ys, color="#777", lw=1.0, alpha=0.7)
    for g in getattr(outside, "geoms", [outside]):
        x, y = g.exterior.xy
        ax.fill(x, y, facecolor="none", edgecolor="#b22", hatch="////", lw=0)
    for g in getattr(park, "geoms", [park]):
        x, y = g.exterior.xy
        ax.plot(x, y, color="#1f5c2e", lw=2.2)
    x, y = dem_cached.exterior.xy
    ax.plot(x, y, color="#6a3d9a", lw=1.4, ls=(0, (6, 3)))
    x, y = LEGACY.exterior.xy
    ax.plot(x, y, color="#111", lw=2.0, ls="--")
    x, y = bridge.exterior.xy
    ax.fill(x, y, color="#333", alpha=0.85)
    ax.plot([82.1], [132.1], marker="^", ms=11, color="#d4560f", mec="#111")
    ax.annotate("木場公園大橋\n(OSM外形 249m・主塔60m)", (118, 200), xytext=(175, 330), fontsize=9,
                arrowprops={"arrowstyle": "->", "color": "#333"})
    ax.plot([0], [0], marker="+", ms=14, color="#000", mew=2)
    ax.annotate("共通原点 (0,0)", (0, 0), xytext=(-170, -40), fontsize=8)

    pct_out = 100 * outside.area / park.area
    legend = [
        plt.Line2D([], [], color="#1f5c2e", lw=2.2, label=f"公園境界 OSM relation/14273608（{park.area:,.0f} m²）"),
        plt.Line2D([], [], color="#111", lw=2, ls="--", label="既存500m四方（旧OSM地物・旧DEM地形の範囲）"),
        Patch(facecolor="none", edgecolor="#b22", hatch="////", label=f"既存範囲外の公園 {pct_out:.1f}%（{outside.area:,.0f} m²）"),
        plt.Line2D([], [], color="#6a3d9a", lw=1.4, ls=(0, (6, 3)), label="既存DEM1Aタイル（z17 3×3枚）の範囲"),
        Patch(color=colors["full"], alpha=0.55, label="100mタイル：既存データで全面カバー"),
        Patch(color=colors["part"], alpha=0.55, label="100mタイル：一部のみカバー"),
        Patch(color=colors["none"], alpha=0.55, label="100mタイル：既存データなし"),
        plt.Line2D([], [], color="#d4560f", marker="^", lw=0, mec="#111", label="G6.2 主塔位置 (x82.1, y132.1)"),
        plt.Line2D([], [], color="#8a6d3b", lw=1, label="既存OSM園路（500m四方に掛かる線のみ）"),
        plt.Line2D([], [], color="#4a90c2", lw=1, label="既存OSM水域"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=7.5, framealpha=0.92)
    ax.set_aspect("equal")
    ax.set_xlim(-330, 420)
    ax.set_ylim(-470, 720)
    ax.set_xlabel("東 x [m]（EPSG:6677ローカル）")
    ax.set_ylabel("北 y [m]")
    ax.grid(color="#ddd", lw=0.4)
    n = {k: sum(1 for *_, f in tiles if (f > 0.999 if k == 'full' else (0 < f <= 0.999 if k == 'part' else f == 0))) for k in colors}
    ax.set_title(f"KIBA PARK REBUILD｜既存データ範囲と公園全域の比較\n100mタイル {len(tiles)}枚：全面 {n['full']}・一部 {n['part']}・なし {n['none']}", fontsize=11)
    ax.text(-325, -465, "© OpenStreetMap contributors (ODbL) ／ 社内確認用・非公開", fontsize=7, color="#555")
    fig.tight_layout()
    fig.savefig(out_png)
    summary = {"park_area_m2": round(park.area, 1), "inside_legacy_m2": round(park.intersection(LEGACY).area, 1),
               "outside_legacy_m2": round(outside.area, 1), "outside_pct": round(pct_out, 2),
               "park_inside_dem1a_cache_pct": round(100 * park.intersection(dem_cached).area / park.area, 2),
               "tiles": len(tiles), "tiles_full": n["full"], "tiles_partial": n["part"], "tiles_none": n["none"],
               "bridge_bounds_local_m": [round(v, 1) for v in bridge.bounds],
               "bridge_inside_legacy": bridge.within(LEGACY),
               "g62_pylon_local_m": [82.1, 132.1]}
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
