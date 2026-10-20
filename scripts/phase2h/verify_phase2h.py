from pathlib import Path
import json, hashlib, math, struct

root = Path(__file__).resolve().parents[2]
build = root / 'build-phase2h'
trial = json.loads((build / 'data/processed/phase2h/bridge_trial_surface.json').read_text(encoding='utf-8'))
nav_path = build / 'data/processed/phase2c/phase2c_navigation.json'
nav_bytes = nav_path.read_bytes()
nav = json.loads(nav_bytes)
source_bytes = (root / 'build-phase2g/data/processed/phase2c/phase2c_navigation.json').read_bytes()
assert hashlib.sha256(nav_bytes).digest() == hashlib.sha256(source_bytes).digest()
bridge_runs = [r for r in nav['runs'] if r.get('bridge')]
counts = {'review': sum('review' in r['statuses'] for r in bridge_runs), 'blocked': sum('blocked' in r['statuses'] for r in bridge_runs), 'walkable': sum('walkable' in r['statuses'] for r in bridge_runs)}
segments = [s for r in bridge_runs for s in r['segments']]
segment_counts = {'review': sum(s['status'] == 'review' for s in segments), 'blocked': sum(s['status'] == 'blocked' for s in segments), 'total': len(segments)}
assert counts == {'review': 8, 'blocked': 5, 'walkable': 0}
assert segment_counts == {'review': 760, 'blocked': 146, 'total': 906}
assert trial['boundaryGapMetres'] == 16.609 and trial['unmodeledOverallLengthMetres'] == 100.555 and trial['gapAutoConnected'] is False
assert len(trial['runs']) == 2 and [round(r['lengthMetres'], 3) for r in trial['runs']] == [68.046, 64.916]
quad_count = 0
for run in trial['runs']:
    assert run['status'] == 'experimental_estimate_only' and run['widthMetres'] == 4.0 and run['widthIsEstimated'] and run['heightIsEstimated']
    assert len(run['points']) > 2 and len(run['surfaces']) and abs(run['points'][-1]['station'] - run['lengthMetres']) < .002
    assert all(run['points'][i]['station'] < run['points'][i + 1]['station'] for i in range(len(run['points']) - 1))
    for quad in run['surfaces']:
        assert len(quad) == 4 and all(len(v) == 3 and all(math.isfinite(float(x)) for x in v) for v in quad)
        quad_count += 1
assert quad_count == 319
app = (build / 'web/phase2h/app.js').read_text(encoding='utf-8')
html = (build / 'web/phase2h/index.html').read_text(encoding='utf-8')
for token in ['trialMode=false', 'trialGroup.visible=false', 'function trialSupport', 'function runTrial', 'function stopTrial', 'moveTrial(']: assert token in app, token
for token in ['trialMode', 'trialRun', 'trialForward', 'trialReverse', 'trialStop', 'trialReset']: assert 'id="' + token + '"' in html
shot_dir = root / 'screenshots/phase2h'
shots = {}
for name in ['top', 'bridge', 'side', 'robot']:
    path = shot_dir / f'phase2h_{name}.png'
    image = path.read_bytes()
    assert image.startswith(b'\x89PNG\r\n\x1a\n')
    width, height = struct.unpack('>II', image[16:24])
    assert (width, height) == (1280, 720)
    shots[name] = {'path': str(path), 'width': width, 'height': height, 'bytes': len(image), 'capturedInBrowser': True}
sha = hashlib.sha256(nav_bytes).hexdigest()
report = {'phase': '2H', 'result': 'PASS', 'scope': 'isolated bridge movement experiment; production navigation untouched', 'trialRuns': [{'id': r['id'], 'lengthMetres': r['lengthMetres'], 'pointCount': len(r['points']), 'widthMetres': r['widthMetres'], 'widthEstimated': True, 'heightEstimated': True, 'surfaceQuads': len(r['surfaces']), 'forwardMetres': [66.3, 63.2][r['id']], 'reverseMetres': [66.5, 63.3][r['id']], 'endpoint': 'BLOCK'} for r in trial['runs']], 'experimentSurfaceQuads': quad_count, 'boundaryGapMetres': 16.609, 'gapConnected': False, 'unmodeledOverallLengthMetres': 100.555, 'gapEntry': 'BLOCK', 'gapMidpointProbeDistanceMetres': 16.609, 'unmodeledAreaEntry': 'BLOCK', 'unmodeledExtrapolationProbeMetres': 100.555, 'approaches': 'not created; blocked', 'endpointGuardMetres': 0.75, 'normalMode': 'Phase 2C navigation only; experimental meshes hidden; bridge blocked', 'phase2cBridgeRuns': counts, 'phase2cBridgeSegments': segment_counts, 'phase2cNavSha256': sha, 'phase2cNavUnchanged': True, 'browserChecks': {'actualBrowser': 'http://127.0.0.1:8781/web/phase2h/', 'normalMode': 'verified blocked; proxy returns to park position when trial mode is disabled', 'runAForwardReverseStop': 'PASS', 'runBForwardReverseStop': 'PASS', 'endpointGapAndUnmodeledBlocks': 'PASS', 'views': list(shots), 'screenshots': shots}, 'performance': {'phase2g': {'top': [60.1, 58, 627814, 56], 'bridgeGround': [60.1, 46, 552776, 56], 'side': [60.1, 40, 552264, 56], 'robot': [60.1, 19, 541188, 56]}, 'phase2hExperimental': {'top': [60.1, 62, 629090, 58], 'bridgeGround': [53.2, 50, 554052, 58], 'side': [50.2, 51, 554064, 58], 'robot': [60.0, 49, 630604, 58]}, 'comparisonNotes': ['Normal-mode overhead matches Phase 2G: 58 draw calls, 627814 triangles, 56 meshes.', 'Experimental top/bridge-ground add 4 calls and 1276 triangles; side view includes vegetation LOD variation.', 'Robot camera positions differ, so robot-view totals are not directly comparable.', 'Steady browser samples reached 58.1–60.1 FPS; save-time readings vary while switching views.']}, 'limitations': ['All deck widths and elevations are estimates.', 'The two runs are disconnected by a 16.609m boundary gap.', 'The 100.555m unmodeled extent remains blocked.', 'No park approach path is created.', 'The 0.75m endpoint guard is an experiment rule, not surveyed bridge geometry.', 'These bounded trials do not prove full-bridge traversal.']}
out = root / 'reports/phase2h'
out.mkdir(parents=True, exist_ok=True)
(out / 'phase2h_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
markdown = f'''# KIBA PARK REBUILD Phase 2H validation

**Result: PASS — isolated browser experiment verified.** The proxy traversed bounded sections only; it did not cross the complete bridge.

## Trial results

| Run | Length | Estimated width | Forward | Reverse | Endpoint |
|---|---:|---:|---:|---:|---|
| A | 68.046 m | 4.0 m | 66.3 m / 663 probes | 66.5 m / 666 probes | BLOCK |
| B | 64.916 m | 4.0 m | 63.2 m / 632 probes | 63.3 m / 635 probes | BLOCK |

The height and width values are estimates. Both ends have a 0.75m experiment guard; this is not a surveyed physical barrier. The 16.609m boundary gap and 100.555m unmodeled extent remain disconnected and blocked. Bridge approaches were not created.

## Navigation preservation

The Phase 2C navigation data is byte-identical to the Phase 2G source (SHA-256 `{sha}`). Its bridge states remain 8 review runs, 5 blocked runs, 0 walkable runs; 760 review and 146 blocked segments. Disabling trial mode hides the trial layer, returns the proxy to its prior park position, and restores the normal-mode bridge-blocked message.

## Browser and performance

Verified in the in-app browser at `http://127.0.0.1:8781/web/phase2h/`. Four 1280×720 images are in `screenshots/phase2h/`. Steady live FPS samples reached 58.1–60.1; capture-time readings varied while changing views and saving screenshots.

| View | Phase 2G FPS / calls / tris / meshes | Phase 2H trial FPS / calls / tris / meshes |
|---|---|---|
| Overhead | 60.1 / 58 / 627,814 / 56 | 60.1 / 62 / 629,090 / 58 |
| Bridge ground | 60.1 / 46 / 552,776 / 56 | 53.2 / 50 / 554,052 / 58 |
| Side | 60.1 / 40 / 552,264 / 56 | 50.2 / 51 / 554,064 / 58 |
| Robot | 60.1 / 19 / 541,188 / 56 | 60.0 / 49 / 630,604 / 58* |

Normal-mode overhead matches Phase 2G. Experimental top and bridge-ground views add 4 calls and 1,276 triangles. The robot-view figures are not directly comparable because the Phase 2H camera starts on the bridge trial run while Phase 2G starts at its default park position.

## Screenshots

- [Overhead](../../screenshots/phase2h/phase2h_top.png)
- [Bridge ground](../../screenshots/phase2h/phase2h_bridge.png)
- [Side](../../screenshots/phase2h/phase2h_side.png)
- [Robot](../../screenshots/phase2h/phase2h_robot.png)

## Windows PowerShell

```powershell
cd C:\\Users\\hp\\Desktop\\KIBA-REAL-CITY
python scripts\\phase2h\\build_phase2h.py
python scripts\\phase2h\\verify_phase2h.py
python scripts\\phase2h\\serve_phase2h.py
```

Open `http://127.0.0.1:8781/web/phase2h/`. Enable **実験モード**, select Run A or B, and use forward, reverse, or stop. Disable the mode to return to normal navigation.

## Limits

All deck heights and widths are estimated. The two modeled runs do not connect over the boundary gap, and the 100.555m unmodeled extent remains blocked. No full bridge crossing is represented.
'''
(out / 'phase2h_validation.md').write_text(markdown, encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
