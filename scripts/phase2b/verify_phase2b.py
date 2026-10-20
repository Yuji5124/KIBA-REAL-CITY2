import json
import argparse
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'data/processed/phase2b').is_dir()), Path(__file__).resolve().parents[1])
parser = argparse.ArgumentParser()
parser.add_argument('--source-root', default=r'C:\Users\hp\Desktop\KIBA-REAL-CITY')
SOURCE = Path(parser.parse_args().source_root)
scene = json.loads((ROOT / 'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))
report = json.loads((ROOT / 'reports/phase2b/phase2b_report.json').read_text(encoding='utf-8'))
t = scene['terrain']
assert t['width'] * t['height'] == len(t['vertices']) == len(t['heightSource'])
assert len(t['faces']) % 3 == 0 and all(0 <= i < len(t['vertices']) for i in t['faces'])
assert report['phase2aReportedFallbackProbeCount'] == report['phase2aFallbackReconstructedCount'] == 1793
assert report['terrainUnresolvedVertices'] == 0
assert report['terrainGridSpacingMetres'][0] <= 1.01
assert report['roadClearance']['minMeasuredAtGeneratedVerticesMetres'] >= 0.079
assert report['roadWidthTaper']['generatedStationWidthRangeMetres'][0] >= 1.0
assert report['bridgeRunCount'] > 0 and report['maxBridgeDeckGrade'] is not None
assert report['roadTerrainGaps']['splitOrOmittedSections'] > 0
assert all('bridge' in r for r in scene['roads'])
assert (SOURCE / 'data/processed/phase2a/phase2a_scene.json').exists()
assert (ROOT / 'reports/phase2b/road_terrain_diagnostics.json').exists()
print(json.dumps({
    'sceneVertices': len(t['vertices']), 'terrainTriangles': len(t['faces']) // 3,
    'terrainSources': report['terrainHeightSources'], 'roads': len(scene['roads']),
    'bridges': report['bridgeRunCount'], 'terrainGaps': report['roadTerrainGaps']['splitOrOmittedSections'],
    'maxGroundGrade': report['maxRoadGrade'], 'maxBridgeGrade': report['maxBridgeDeckGrade'],
    'verification': 'PASS'
}, ensure_ascii=False, indent=2))
