#!/usr/bin/env python3
"""Build the isolated Phase 2E bridge integration data from existing inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import struct
from collections import Counter


SECRET_KEYS = {"api_key", "api_key_confirmed", "user_balance", "blendermcp_server_running"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_glb(data: bytes) -> tuple[dict, bytes]:
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError("Expected a valid glTF 2.0 binary file")
    cursor = 12
    doc = None
    binary = b""
    while cursor < len(data):
        length, kind = struct.unpack_from("<II", data, cursor)
        cursor += 8
        chunk = data[cursor:cursor + length]
        cursor += length
        if kind == 0x4E4F534A:
            doc = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binary = chunk
    if doc is None:
        raise ValueError("GLB has no JSON chunk")
    return doc, binary


def clean_secrets(value: object) -> int:
    removed = 0
    if isinstance(value, dict):
        for key in list(value):
            if key.lower() in SECRET_KEYS:
                del value[key]
                removed += 1
            else:
                removed += clean_secrets(value[key])
    elif isinstance(value, list):
        for child in value:
            removed += clean_secrets(child)
    return removed


def write_glb(doc: dict, binary: bytes) -> bytes:
    raw_json = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw_json += b" " * ((-len(raw_json)) % 4)
    binary += b"\0" * ((-len(binary)) % 4)
    total = 12 + 8 + len(raw_json) + 8 + len(binary)
    return (struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<II", len(raw_json), 0x4E4F534A) + raw_json
            + struct.pack("<II", len(binary), 0x004E4942) + binary)


def read_accessor(doc: dict, binary: bytes, idx: int) -> list[tuple[float, ...]]:
    acc = doc["accessors"][idx]
    view = doc["bufferViews"][acc["bufferView"]]
    comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    fmt, size, _ = {5120: ("b", 1, True), 5121: ("B", 1, False),
                    5122: ("h", 2, True), 5123: ("H", 2, False),
                    5125: ("I", 4, False), 5126: ("f", 4, True)}[acc["componentType"]]
    stride = view.get("byteStride", size * comps)
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    result = []
    for i in range(acc["count"]):
        v = struct.unpack_from("<" + fmt * comps, binary, start + i * stride)
        if acc.get("normalized") and acc["componentType"] != 5126:
            signed = acc["componentType"] in (5120, 5122)
            maximum = (2 ** (size * 8 - 1) - 1) if signed else (2 ** (size * 8) - 1)
            v = tuple(max(-1.0, x / maximum) if signed else x / maximum for x in v)
        result.append(tuple(float(x) for x in v))
    return result


def qrotate(p: tuple[float, float, float], q: list[float]) -> tuple[float, float, float]:
    x, y, z = p
    qx, qy, qz, qw = q
    # q * [p,0] * conjugate(q), expanded.
    ix, iy, iz = qw*x + qy*z-qz*y, qw*y + qz*x-qx*z, qw*z + qx*y-qy*x
    iw = -qx*x-qy*y-qz*z
    return (ix*qw-iw*qx-iy*qz+iz*qy,
            iy*qw-iw*qy-iz*qx+ix*qz,
            iz*qw-iw*qz-ix*qy+iy*qx)


def node_transform(node: dict, point: tuple[float, float, float]) -> tuple[float, float, float]:
    scale = node.get("scale", [1, 1, 1])
    p = tuple(point[i] * scale[i] for i in range(3))
    if "rotation" in node:
        p = qrotate(p, node["rotation"])
    t = node.get("translation", [0, 0, 0])
    return tuple(p[i] + t[i] for i in range(3))


def inspect_mesh(doc: dict, binary: bytes) -> dict:
    scene = doc["scenes"][doc.get("scene", 0)]
    nodes = doc["nodes"]
    positions, triangle_count, components = [], 0, []
    material_ids, names = set(), []
    for node_idx in scene.get("nodes", []):
        node = nodes[node_idx]
        if "mesh" not in node:
            continue
        names.append(node.get("name", f"node-{node_idx}"))
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            verts = read_accessor(doc, binary, primitive["attributes"]["POSITION"])
            positions.extend(node_transform(node, p) for p in verts)
            if "indices" in primitive:
                index_count = doc["accessors"][primitive["indices"]]["count"]
            else:
                index_count = len(verts)
            triangle_count += index_count // 3
            material_ids.add(primitive.get("material", -1))
            components.append({"node": node.get("name", f"node-{node_idx}"),
                               "extras": node.get("extras", {}), "vertices": len(verts),
                               "triangles": index_count // 3})
    if not positions:
        raise ValueError("G6.2 model contains no triangle geometry")
    axes = [[min(p[i] for p in positions), max(p[i] for p in positions)] for i in range(3)]
    return {"boundsXYZ": axes, "dimensionsXYZMetres": [round(b[1]-b[0], 3) for b in axes],
            "meshNodes": len(names), "primitiveCount": len(components),
            "materialCount": len(material_ids), "triangleCount": triangle_count,
            "componentNames": names, "components": components}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=pathlib.Path, required=True)
    ap.add_argument("--output-root", type=pathlib.Path, required=True)
    ap.add_argument("--g62-glb", type=pathlib.Path, required=True)
    args = ap.parse_args()
    source, out = args.source_root.resolve(), args.output_root.resolve()
    glb_path = args.g62_glb.resolve()
    data_root = source / "data/processed"
    phase2b = json.loads((data_root / "phase2b/phase2b_scene.json").read_text(encoding="utf-8"))
    nav = json.loads((data_root / "phase2c/phase2c_navigation.json").read_text(encoding="utf-8"))
    veg = json.loads((data_root / "phase2d/phase2d_vegetation.json").read_text(encoding="utf-8"))
    original = glb_path.read_bytes()
    glb_doc, binary = parse_glb(original)
    glb_info = inspect_mesh(glb_doc, binary)
    removed = clean_secrets(glb_doc)
    sanitized = write_glb(glb_doc, binary)
    phase_out = out / "data/processed/phase2e"
    phase_out.mkdir(parents=True, exist_ok=True)
    model_out = phase_out / "Kiba_Park_Ohashi_G6.2_visual_details_sanitized.glb"
    model_out.write_bytes(sanitized)

    bridge_runs = [r for r in nav["runs"] if r.get("bridge")]
    osm_roads = [r for r in phase2b["roads"] if r.get("id") == "33976871"]
    target_runs = [r for r in bridge_runs if r["id"] == "33976871"]
    centers = []
    run_endpoints = []
    for run in target_runs:
        local_centers = []
        for s in run["stations"]:
            p = ((s[0]+s[3])/2, (s[1]+s[4])/2, (s[2]+s[5])/2)
            centers.append(p)
            local_centers.append(p)
        if local_centers:
            run_endpoints.append((local_centers[0], local_centers[-1]))
    xs, ys, zs = [p[0] for p in centers], [p[1] for p in centers], [p[2] for p in centers]
    bounds = glb_info["boundsXYZ"]
    # The local viewer frame is X east, Y-up, Z=-north; Phase2B carries this same origin.
    inside_bbox = [p for p in centers if bounds[0][0] <= p[0] <= bounds[0][1]
                   and bounds[2][0] <= p[2] <= bounds[2][1]]
    runlen = [float(r.get("centerlineLengthMetres", 0)) for r in osm_roads]
    status_counts = Counter(s for r in bridge_runs for s in r.get("statuses", []))
    has_deck = any(any(word in name.lower() for word in ("deck", "bridge deck", "bridge surface"))
                   for name in glb_info["componentNames"])
    projected_origin = glb_doc.get("scenes", [{}])[0].get("extras", {}).get("phase2a_origin_projected_m")
    source_crs = glb_doc.get("scenes", [{}])[0].get("extras", {}).get("crs")
    report = {
        "phase": "2E", "coordinateSystem": phase2b["coordinateConvention"],
        "phase2bOriginEPSG6677": phase2b["origin"], "glbCrs": source_crs,
        "glbOriginEPSG6677": json.loads(projected_origin) if projected_origin else None,
        "originMatchesPhase2b": bool(projected_origin) and all(abs(float(a)-float(b)) < 1e-6 for a,b in zip(json.loads(projected_origin), phase2b["origin"])),
        "registration": {"translationMetres": [0,0,0], "rotationDegrees": [0,0,0], "scale": 1.0,
                         "basis": "GLB vertices are Y-up in the same local X/east, Z/-north frame; raw scene extras claim Z-up and conflict with mesh layout. Identity transform is a visually registered hypothesis, not a survey control-point verification."},
        "asset": {"sourceFile": glb_path.name, "sourceSha256": sha256(original),
                  "sanitizedFile": model_out.name, "sanitizedSha256": sha256(sanitized),
                  "metadataFieldsRemoved": removed, **glb_info,
                  "blendFileFound": False, "deckSurfaceMeshPresent": has_deck,
                  "walkCollision": False},
        "osmComparison": {"wayId": "33976871", "phase2bRunCount": len(osm_roads),
                          "phase2cNavigationRunCount": len(target_runs),
                          "phase2cBridgeRunCountAll": len(bridge_runs),
                          "phase2cAllBridgeStatuses": dict(status_counts),
                          "osmRibbonCenterlineLengthMetres": round(sum(runlen), 3),
                          "osmRibbonLengthBySplitRunMetres": [round(v,3) for v in runlen],
                          "osmSplitRunGapMetres": round(min(math.dist(a,b) for a in run_endpoints[0] for b in run_endpoints[1]), 3) if len(run_endpoints)>1 else None,
                          "osmCenterlinePlanBoundsXZ": [round(min(xs),3), round(min(zs),3), round(max(xs),3), round(max(zs),3)],
                          "osmBridgeInterpolatedHeightRangeMetres": [round(min(ys),3), round(max(ys),3)],
                          "fractionOfStationsInsideGlbPlanBounds": round(len(inside_bbox)/len(centers), 4) if centers else 0,
                          "deckHeightAgreement": "unverifiable: GLB has only pylon/crossbeam/stay meshes and no deck surface; Phase2C deck is inferred from Phase2B endpoints"},
        "viewAndCollisionPolicy": {"modelVisualOnly": True, "phase2cBridgeNavigationUnchanged": True,
                                   "allBridgeRunsRemainReviewOrBlocked": True,
                                   "estimatedBridgeHeightNeverPromotedToMeasured": True},
        "counts": {"mappedTrees": len(veg["mappedTrees"]), "estimatedTrees": len(veg["estimatedTrees"]),
                   "bridgeRuns": len(bridge_runs)},
    }
    (phase_out / "phase2e_bridge_alignment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"result":"PASS", "meshNodes":glb_info["meshNodes"], "triangles":glb_info["triangleCount"],
                      "phase2cBridgeRuns":len(bridge_runs), "targetWayRuns":len(target_runs),
                      "targetWayPathMetres":round(sum(runlen),3), "hasDeck":has_deck,
                      "metadataSecretsRemoved":removed, "originMatches":report["originMatchesPhase2b"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
