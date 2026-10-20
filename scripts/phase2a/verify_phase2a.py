import json,sys
from pathlib import Path
p=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[2]);d=json.loads((p/'data/processed/phase2a/phase2a_scene.json').read_text(encoding='utf-8'));r=json.loads((p/'data/processed/phase2a/phase2a_report.json').read_text(encoding='utf-8'));t=d['terrain'];checks={
 'measured heights preserved':r['phase1MeasuredHeightMaxDifferenceMetres']==0 and r['measuredVertices']==3640,
 'all missing vertices interpolated':r['interpolatedVertices']==92 and r['unresolvedVertices']==0 and all(t['heightSource'][i]=='interpolated' for i in t['interpolatedIndices']),
 'missing terrain cells closed':r['terrainGapCellsPhase2']==0 and len(t['faces'])//3>r['terrainFaceCountPhase1'],
 'all Phase 1 path ways rebuilt':r['roadInputWayCount']==143 and r['roadRibbonRunCount']>0,
 'road mesh arrays valid':all(len(q['stations'])>=2 and len(q['indices'])%3==0 for q in d['roads']),
 'no negative designed edge clearance':r['roadClearanceMetres']['negativeClearanceSamples']==0 and r['roadClearanceMetres']['observedMin']>=.06,
 '3D viewer built':(p/'build-phase2a/web/phase2a/index.html').exists() and (p/'build-phase2a/data/processed/phase2a/phase2a_scene.json').exists(),
}
for k,v in checks.items():print(('PASS' if v else 'FAIL')+' '+k)
print(f"terrain triangles {len(t['faces'])//3}; road runs {len(d['roads'])}; road triangles {r['roadMeshTriangles']}; edge fallback samples {r['terrainFallbackSamplesForRoadEdges']}")
if not all(checks.values()):sys.exit(1)
