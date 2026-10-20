"""KIBA PARK REBUILD - layered OSM fetch (run on the Windows PC).  v1 (2026-10-18)

Replaces the single large Overpass query of fetch_phase1_data.py
(osm/kiba_region_overpass.osm, which kept failing) with small per-layer queries:
  paths / buildings / vegetation / water / facilities, each split into sub-queries.
Every sub-query is written to its own file  data/raw/osm/layers/<layer>/<name>.osm.

Resume rules:
  * A file that already exists and is a valid Overpass result is NEVER re-fetched
    or overwritten -> re-running retries only the missing / failed parts.
  * An existing but invalid file is kept as-is and reported (not overwritten);
    move it aside by hand if you want it re-fetched.
  * The park relation file (osm/kiba_park_relation_14273608.osm) is not touched.

Safety (shared with fetch_phase1_data.py): writes only inside <project>/data/raw,
refuses to run from KIBA-REAL-CITY-main, .part file + validation before rename,
sequential requests, pause between queries, backoff on 429/5xx, no deletion.

Usage (PowerShell, project folder):
    python scripts/fetch/fetch_osm_layers.py --dry-run                 # plan + cache status, no network
    python scripts/fetch/fetch_osm_layers.py                           # fetch missing parts only
    python scripts/fetch/fetch_osm_layers.py --only paths water        # restrict to layers
Needs: Python 3.10+, pyproj.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_phase1_data import OVERPASS, RAW, ROOT, UA, guard_paths, region_latlon, safe_target  # noqa: E402

VERSION = "kpr-fetch-osm/1"
TIMEOUT_S = 90       # Overpass server-side timeout per sub-query
PAUSE_S = 5.0        # between queries (be polite to the public Overpass servers)
RETRIES = 4

PATH_TYPES = "footway|path|pedestrian|steps|cycleway|track|bridleway|corridor"
VEG_NATURAL = "wood|scrub|grassland|heath"
VEG_LANDUSE = "grass|forest|meadow|flowerbed|village_green"

# layer -> {sub-query name: Overpass statements (bbox is set globally)}
LAYERS: dict[str, dict[str, str]] = {
    "paths": {
        "footpaths": f'way["highway"~"^({PATH_TYPES})$"];',
        "roads": f'way["highway"]["highway"!~"^({PATH_TYPES})$"];',
        "highway_nodes": 'node["highway"];',
        "bridges": 'way["man_made"="bridge"];relation["man_made"="bridge"];way["bridge"];',
    },
    "buildings": {
        "buildings": 'way["building"];relation["building"];',
        "building_parts": 'way["building:part"];relation["building:part"];',
    },
    "vegetation": {
        "areas": (f'way["natural"~"^({VEG_NATURAL})$"];relation["natural"~"^({VEG_NATURAL})$"];'
                  f'way["landuse"~"^({VEG_LANDUSE})$"];relation["landuse"~"^({VEG_LANDUSE})$"];'
                  'way["leisure"="garden"];relation["leisure"="garden"];'),
        "trees": 'node["natural"="tree"];way["natural"="tree_row"];',
    },
    "water": {
        "water_areas": 'way["natural"="water"];relation["natural"="water"];way["water"];relation["water"];',
        "waterways": 'way["waterway"];relation["waterway"];node["waterway"];',
        "fountains": 'nwr["amenity"="fountain"];',
    },
    "facilities": {
        "leisure": 'nwr["leisure"];',
        "amenity": 'nwr["amenity"];',
        "tourism": 'nwr["tourism"];nwr["information"];',
        "barriers": 'nwr["barrier"];',
        "man_made": 'nwr["man_made"]["man_made"!="bridge"];',
    },
}


def build_requests(bbox, only: list[str] | None):
    w, s, e, n = bbox
    head = f"[out:xml][timeout:{TIMEOUT_S}][bbox:{s:.7f},{w:.7f},{n:.7f},{e:.7f}];"
    reqs = []
    for layer, subs in LAYERS.items():
        if only and layer not in only:
            continue
        for name, stmts in subs.items():
            reqs.append({"kind": "osm", "layer": layer, "name": name,
                         "query": f"{head}({stmts});(._;>;);out meta;",
                         "path": f"osm/layers/{layer}/{name}.osm"})
    return reqs


def check_osm(data: bytes) -> tuple[bool, str, dict]:
    """Valid = OSM XML root and no Overpass runtime remark. An empty result is valid
    (a layer may simply have no features); the counts are recorded."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return False, f"XML parse error: {exc}", {}
    if root.tag != "osm":
        return False, f"unexpected root <{root.tag}>", {}
    remark = root.find("remark")
    if remark is not None and remark.text and ("error" in remark.text.lower() or "timed out" in remark.text.lower()):
        return False, f"Overpass remark: {remark.text.strip()[:200]}", {}
    counts = {t: sum(1 for _ in root.iter(t)) for t in ("node", "way", "relation")}
    return True, "", counts


def overpass_post(query: str) -> bytes:
    last = None
    for attempt in range(RETRIES):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            body = urllib.parse.urlencode({"data": query}).encode()
            with urlopen(Request(url, data=body, headers=UA), timeout=TIMEOUT_S + 60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = exc
            wait = 30 * (attempt + 1) if exc.code in (429, 504) else 10 * (attempt + 1)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            wait = 10 * (attempt + 1)
        print(f"    retry {attempt + 1}/{RETRIES} in {wait}s via next endpoint ({last})")
        time.sleep(wait)
    raise RuntimeError(str(last))


def cache_status(target: Path) -> tuple[str, str, dict]:
    if not target.is_file():
        return "missing", "", {}
    ok, why, counts = check_osm(target.read_bytes())
    return ("cached", "", counts) if ok else ("invalid", why, {})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show plan and cache status, no network")
    ap.add_argument("--only", nargs="+", choices=list(LAYERS), help="restrict to these layers")
    args = ap.parse_args()
    guard_paths()
    bbox = region_latlon()
    reqs = build_requests(bbox, args.only)
    for r in reqs:
        r["target"] = safe_target(r["path"])  # validate every path before any network access
    print(f"project : {ROOT}\nwrite to: {RAW / 'osm' / 'layers'}\n"
          f"bbox W,S,E,N: {tuple(round(v, 7) for v in bbox)}\nsub-queries: {len(reqs)}")

    status = {r["path"]: cache_status(r["target"]) for r in reqs}
    if args.dry_run:
        for r in reqs:
            st, why, counts = status[r["path"]]
            extra = f" {counts}" if counts else (f" ({why})" if why else "")
            print(f"  {st:8} {r['layer']:10} {r['name']:15} -> data/raw/{r['path']}{extra}")
            print(f"           {r['query']}")
        todo = sum(1 for v in status.values() if v[0] == "missing")
        print(f"\nDRY-RUN: {todo} to fetch, "
              f"{sum(1 for v in status.values() if v[0] == 'cached')} cached (skipped), "
              f"{sum(1 for v in status.values() if v[0] == 'invalid')} invalid (kept, skipped)")
        return

    manifest = {"tool": VERSION, "started_utc": datetime.now(timezone.utc).isoformat(), "bbox_lonlat_WSEN": bbox,
                "source": {"via": "Overpass API (read-only)", "license": "ODbL 1.0",
                           "attribution": "(c) OpenStreetMap contributors",
                           "url": "https://www.openstreetmap.org/copyright"},
                "files": [], "failures": []}
    first = True
    for i, r in enumerate(reqs, 1):
        tag = f"[{i}/{len(reqs)}] {r['layer']}/{r['name']}"
        entry = {k: r[k] for k in ("layer", "name", "path", "query")}
        st, why, counts = status[r["path"]]
        if st == "cached":
            data = r["target"].read_bytes()
            manifest["files"].append({**entry, **counts, "bytes": len(data),
                                      "sha256": hashlib.sha256(data).hexdigest(), "status": "cached"})
            print(f"{tag} cached {counts}")
            continue
        if st == "invalid":
            manifest["failures"].append({**entry, "error": f"existing file invalid, not overwritten: {why}"})
            print(f"{tag} existing file invalid, kept as-is ({why})")
            continue
        if not first:
            time.sleep(PAUSE_S)
        first = False
        try:
            data = overpass_post(r["query"])
        except RuntimeError as exc:
            manifest["failures"].append({**entry, "error": str(exc)})
            print(f"{tag} FAIL {exc}")
            continue
        ok, why, counts = check_osm(data)
        if not ok:
            manifest["failures"].append({**entry, "error": why, "bytes": len(data)})
            print(f"{tag} INVALID ({why})")
            continue
        r["target"].parent.mkdir(parents=True, exist_ok=True)
        part = r["target"].with_name(r["target"].name + ".part")
        part.write_bytes(data)
        part.replace(r["target"])
        manifest["files"].append({**entry, **counts, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                  "status": "downloaded", "retrieved_utc": datetime.now(timezone.utc).isoformat()})
        print(f"{tag} ok {counts} ({len(data):,} B)")

    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    mdir = RAW / "osm" / "layers"
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / "osm_fetch_manifest.json"
    if mpath.exists():  # keep earlier manifests, never overwrite
        mpath.rename(mdir / f"osm_fetch_manifest_{int(mpath.stat().st_mtime)}.json")
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDONE: {len(manifest['files'])} ok, {len(manifest['failures'])} failures -> {mpath.relative_to(ROOT)}")
    if manifest["failures"]:
        print("Run this script again later - finished sub-queries are reused, only failed ones are retried.")
        sys.exit(2)


if __name__ == "__main__":
    main()
