import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'data/processed/phase2c/phase2c_navigation.json').is_file())
nav = json.loads((ROOT / 'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))
report = json.loads((ROOT / 'reports/phase2c/phase2c_report.json').read_text(encoding='utf-8'))
phase2b = json.loads((ROOT / 'reports/phase2b/phase2b_report.json').read_text(encoding='utf-8'))

assert report['renderTerrainModified'] is False
assert report['rawDEMModified'] is False
assert report['terrainGradeAudit']['reconstructedTransitionsOver20Percent'] == phase2b['groundRoadTransitionsOver20Percent'] == 86
assert report['terrainGradeAudit']['reconstructedTransitionsOver35Percent'] == phase2b['groundRoadTransitionsOver35Percent'] == 17
assert report['navigation']['bridgeRuns'] == 13
assert report['navigation']['gapBlockers'] == 22
assert report['navigation']['routeGapsAutoConnected'] is False
assert report['navigation']['testRouteMetres'] <= 24.0
assert report['navigation']['maxRequiredCorrectionsMetres'] <= .12
assert report['navigation']['bridgeMaximumGrade'] < .1
assert len(nav['blockedAreas']) == 22 and all(not g['autoConnected'] for g in nav['blockedAreas'])
assert len([r for r in nav['runs'] if r['bridge']]) == 13
assert all(r['heightBasis'] == 'phase2b_endpoint_linear_inference' for r in nav['runs'] if r['bridge'])
assert all(s['status'] == 'blocked' for r in nav['runs'] if r['stairs'] for s in r['segments'])
assert nav['testRoute'] and nav['testRoute']['status'] == 'walkable'
counts = report['navigation']['segmentCounts']
assert sum(counts.values()) == sum(len(r['segments']) for r in nav['runs'])
print(json.dumps({'result':'PASS','phase2bGroundGradeCountsReproduced':[86,17], 'navigationSegments':counts, 'bridgeRuns':13,'gapBlockers':22,'testRouteMetres':nav['testRoute']['lengthMetres'],'maxCorrectionMetres':report['navigation']['maxRequiredCorrectionsMetres']},ensure_ascii=False,indent=2))
