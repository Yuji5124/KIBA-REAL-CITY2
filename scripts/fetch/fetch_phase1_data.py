"""KIBA PARK REBUILD - Phase 1 data fetch (run on the Windows PC).  v2 (2026-10-17)

Downloads ONLY into <this project>/data/raw/ (never into KIBA-REAL-CITY-main):
  1. OpenStreetMap data for Kiba Park (relation/14273608) + 60 m margin, via the
     read-only Overpass API (the OSM editing API /map is meant for editors, so it
     is no longer used). 2 queries in total.
  2. GSI elevation tiles DEM1A (z17) and DEM5A (z15) for the same area (17 tiles).
  3. GSI seamless aerial photo tiles (z18, 50 tiles) for vegetation-density
     ANALYSIS ONLY (not baked into models, not published). Optional: --skip-photo.

Safety:
  * Every output path is resolved and must be inside <project>/data/raw.
  * Refuses to run if the project folder is the legacy KIBA-REAL-CITY-main.
  * Downloads go to a .part file and are renamed only after validation
    (PNG/JPEG signature, OSM XML root) -> an interrupted run never leaves a
    half file that looks complete. Re-running resumes; finished files are reused.
  * Sequential requests only, 1 s pause, retries with backoff on 429/5xx.
  * No package installation, no deletion, no overwrite of existing valid files.

Usage (PowerShell, project folder):
    python scripts/fetch/fetch_phase1_data.py --dry-run     # show plan only
    python scripts/fetch/fetch_phase1_data.py               # download
    python scripts/fetch/fetch_phase1_data.py --skip-photo  # without aerial photos
    python scripts/fetch/verify_phase1_data.py              # verify afterwards
Needs: Python 3.10+, pyproj.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import kpr_coords as C  # noqa: E402

RAW = (ROOT / "data" / "raw").resolve()
VERSION = "kpr-fetch/2"
UA = {"User-Agent": f"KIBA-PARK-REBUILD/{VERSION} (personal non-commercial 3D terrain research; local use)"}
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
# Park bounds (local m) from OSM relation/14273608 - see docs/phase0/COORDINATE_SYSTEM.md
PARK_BOUNDS = (-136.18, -353.97, 255.24, 636.89)
MARGIN_M = 60.0
PAUSE_S = 1.0
RETRIES = 4


def guard_paths() -> None:
    if ROOT.name.lower().endswith("-main"):
        sys.exit(f"REFUSED: {ROOT} looks like the legacy KIBA-REAL-CITY-main. Run from the new project.")
    if not (ROOT / "CLAUDE.md").is_file() or not (ROOT / "docs" / "phase0").is_dir():
        sys.exit(f"REFUSED: {ROOT} is not the KIBA PARK REBUILD project folder.")


def safe_target(rel: str) -> Path:
    p = (RAW / rel).resolve()
    if RAW not in p.parents:
        raise ValueError(f"path escapes data/raw: {p}")
    return p


def region_latlon():
    x0, y0, x1, y1 = PARK_BOUNDS
    x0, y0, x1, y1 = x0 - MARGIN_M, y0 - MARGIN_M, x1 + MARGIN_M, y1 + MARGIN_M
    pts = [C.local_to_latlon(x, y) for x in (x0, x1) for y in (y0, y1)]
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    return min(lons), min(lats), max(lons), max(lats)  # W, S, E, N


def tile_xy(lon, lat, z):
    n = 1 << z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return int(x), int(y)


def tiles(bbox, z):
    w, s, e, n = bbox
    xa, ya = tile_xy(w, n, z)
    xb, yb = tile_xy(e, s, z)
    return [(z, x, y) for x in range(xa, xb + 1) for y in range(ya, yb + 1)]


def plan(skip_photo: bool):
    w, s, e, n = region_latlon()
    reqs = []
    area_q = (f"[out:xml][timeout:120];(nwr({s:.7f},{w:.7f},{n:.7f},{e:.7f}););(._;>;);out meta;")
    rel_q = "[out:xml][timeout:60];relation(14273608);(._;>;);out meta;"
    reqs.append({"kind": "osm", "query": area_q, "path": "osm/kiba_region_overpass.osm"})
    reqs.append({"kind": "osm", "query": rel_q, "path": "osm/kiba_park_relation_14273608.osm"})
    for layer, z in (("dem1a_png", 17), ("dem5a_png", 15)):
        for z_, x, y in tiles((w, s, e, n), z):
            reqs.append({"kind": "dem", "url": f"https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z_}/{x}/{y}.png",
                         "path": f"gsi/{layer}/{z_}/{x}/{y}.png"})
    if not skip_photo:
        for z_, x, y in tiles((w, s, e, n), 18):
            reqs.append({"kind": "photo", "url": f"https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z_}/{x}/{y}.jpg",
                         "path": f"gsi/seamlessphoto/{z_}/{x}/{y}.jpg"})
    return (w, s, e, n), reqs


def valid(kind: str, data: bytes) -> bool:
    if kind == "dem":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if kind == "photo":
        return data[:3] == b"\xff\xd8\xff"
    if kind == "osm":
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            return False
        return root.tag == "osm" and any(True for _ in root.iter("node"))
    return False


def http_get(req: dict) -> tuple[int, bytes]:
    """Returns (status, body). status 404 means 'no data for this tile' (normal for sea/void)."""
    endpoints = OVERPASS if req["kind"] == "osm" else [req["url"]]
    last = None
    for attempt in range(RETRIES):
        url = endpoints[attempt % len(endpoints)]
        try:
            if req["kind"] == "osm":
                body = urllib.parse.urlencode({"data": req["query"]}).encode()
                r = Request(url, data=body, headers=UA)
            else:
                r = Request(url, headers=UA)
            with urlopen(r, timeout=180) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return 404, b""
            last = exc
            wait = 15 * (attempt + 1) if exc.code in (429, 504) else 5 * (attempt + 1)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            wait = 5 * (attempt + 1)
        print(f"    retry {attempt + 1}/{RETRIES} in {wait}s ({last})")
        time.sleep(wait)
    raise RuntimeError(str(last))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-photo", action="store_true")
    args = ap.parse_args()
    guard_paths()
    bbox, reqs = plan(args.skip_photo)
    counts: dict[str, int] = {}
    for r in reqs:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    print(f"project : {ROOT}\nwrite to: {RAW}\nbbox W,S,E,N: {tuple(round(v, 7) for v in bbox)}\nrequests: {counts}")
    for r in reqs:
        safe_target(r["path"])  # validate every path before any network access
    if args.dry_run:
        for r in reqs:
            print(f"  {r['kind']:5} {r.get('url', 'overpass')} -> data/raw/{r['path']}")
        return

    manifest_path = RAW / "fetch_manifest.json"
    manifest = {"tool": VERSION, "started_utc": datetime.now(timezone.utc).isoformat(), "bbox_lonlat_WSEN": bbox,
                "crs_local": C.CRS_PROJECTED, "origin_projected_m": [C.ORIGIN_E, C.ORIGIN_N],
                "sources": {
                    "osm": {"via": "Overpass API (read-only)", "license": "ODbL 1.0",
                            "attribution": "(c) OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright"},
                    "dem": {"via": "地理院タイル 標高タイル", "attribution": "国土地理院（標高タイル）を加工して作成",
                            "terms": "国土地理院コンテンツ利用規約 / 測量法の承認が必要な場合あり（公開前に要確認）"},
                    "photo": {"via": "地理院タイル 全国最新写真（シームレス）", "attribution": "国土地理院",
                              "use": "植生密度の解析のみ。モデルへの焼き込み・再配布はしない"}},
                "files": [], "nodata_404": [], "failures": []}
    for i, r in enumerate(reqs, 1):
        target = safe_target(r["path"])
        tag = f"[{i}/{len(reqs)}]"
        if target.is_file():
            data = target.read_bytes()
            if valid(r["kind"], data):
                manifest["files"].append({**{k: v for k, v in r.items() if k != "query"}, "bytes": len(data),
                                          "sha256": hashlib.sha256(data).hexdigest(), "status": "cached"})
                print(f"{tag} cached  data/raw/{r['path']}")
                continue
            print(f"{tag} existing file is invalid, keeping it as-is and skipping: data/raw/{r['path']}")
            manifest["failures"].append({**r, "error": "existing file invalid (not overwritten)"})
            continue
        try:
            status, data = http_get(r)
        except RuntimeError as exc:
            manifest["failures"].append({**{k: v for k, v in r.items() if k != "query"}, "error": str(exc)})
            print(f"{tag} FAIL    {r['path']} {exc}")
            continue
        finally:
            time.sleep(PAUSE_S)
        if status == 404:
            manifest["nodata_404"].append(r["path"])
            print(f"{tag} no data (404) {r['path']}")
            continue
        if not valid(r["kind"], data):
            manifest["failures"].append({**{k: v for k, v in r.items() if k != "query"}, "error": "content validation failed"})
            print(f"{tag} INVALID {r['path']} ({len(data)} B)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        part.write_bytes(data)
        part.replace(target)
        manifest["files"].append({**{k: v for k, v in r.items() if k != "query"}, "bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest(), "status": "downloaded",
                                  "retrieved_utc": datetime.now(timezone.utc).isoformat()})
        print(f"{tag} ok      data/raw/{r['path']} ({len(data):,} B)")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    RAW.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():  # keep earlier manifests, never overwrite
        manifest_path.rename(RAW / f"fetch_manifest_{int(manifest_path.stat().st_mtime)}.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = len(manifest["files"])
    print(f"\nDONE: {ok} files ok, {len(manifest['nodata_404'])} no-data, {len(manifest['failures'])} failures")
    print("Next: python scripts/fetch/verify_phase1_data.py")
    if manifest["failures"]:
        print("Some downloads failed. Simply run this script again later - finished files are reused.")
        sys.exit(2)


if __name__ == "__main__":
    main()
