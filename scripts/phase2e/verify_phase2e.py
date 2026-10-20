#!/usr/bin/env python3
"""Validate the isolated Phase 2E bridge package and its safety invariants."""
from __future__ import annotations
import json, pathlib, struct, sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2])
phase = root / 'data/processed/phase2e'
report = json.loads((phase / 'phase2e_bridge_alignment.json').read_text(encoding='utf-8'))
nav = json.loads((root / 'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))
scene = json.loads((root / 'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))
glb = (phase / report['asset']['sanitizedFile']).read_bytes()
magic, version, total = struct.unpack_from('<4sII', glb, 0)
assert magic == b'glTF' and version == 2 and total == len(glb), 'invalid sanitized GLB header'
json_len, json_type = struct.unpack_from('<II', glb, 12)
assert json_type == 0x4E4F534A, 'missing GLB JSON chunk'
doc = json.loads(glb[20:20+json_len].decode('utf-8'))
serialized = json.dumps(doc).lower()
assert 'api_key' not in serialized and 'user_balance' not in serialized, 'sensitive metadata remains in package'
assert report['originMatchesPhase2b'], 'GLB projected origin differs from Phase 2B'
assert report['asset']['meshNodes'] == 27 and report['asset']['triangleCount'] == 356
assert report['asset']['deckSurfaceMeshPresent'] is False and report['asset']['walkCollision'] is False
bridges = [r for r in nav['runs'] if r.get('bridge')]
target = [r for r in bridges if r['id'] == '33976871']
assert len(bridges) == 13 and len(target) == 2
assert all(set(r['statuses']) <= {'review', 'blocked'} for r in bridges), 'bridge became traversable'
assert report['osmComparison']['phase2cBridgeRunCountAll'] == len(bridges)
assert report['osmComparison']['wayId'] == '33976871'
assert report['osmComparison']['deckHeightAgreement'].startswith('unverifiable:')
assert len(scene['origin']) == 2
print(json.dumps({'result':'PASS','glbMeshes':report['asset']['meshNodes'],'triangles':report['asset']['triangleCount'],
 'bridgeRuns':len(bridges),'targetWayRuns':len(target),'originMatches':report['originMatchesPhase2b'],
 'deckMeshPresent':report['asset']['deckSurfaceMeshPresent'],'estimatedDeckIsReviewOnly':True,
 'secretsAbsentFromCopy':True},ensure_ascii=False,indent=2))
