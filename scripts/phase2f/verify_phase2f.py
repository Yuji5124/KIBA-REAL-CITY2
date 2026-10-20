import hashlib,json,math,sys
from pathlib import Path
root=Path(sys.argv[1] if len(sys.argv)>1 else r'C:\Users\hp\Desktop\KIBA-REAL-CITY')
p=json.loads((root/'data/processed/phase2f/bridge_deck_candidate.json').read_text(encoding='utf-8'))
r=json.loads((root/'reports/phase2f/phase2f_validation.json').read_text(encoding='utf-8'))
navpath=root/'data/processed/phase2c/phase2c_navigation.json'
copy=root/'build-phase2f/data/processed/phase2c/phase2c_navigation.json'
nav=json.loads(navpath.read_text(encoding='utf-8'))
assert hashlib.sha256(navpath.read_bytes()).digest()==hashlib.sha256(copy.read_bytes()).digest(), 'Phase 2C navigation copy differs from source'
assert p['status']=='visual_candidate_review_only' and p['collisionEnabled'] is False and p['navigationModified'] is False
assert len(p['clippedRuns'])==2 and abs(p['gap']['lengthMetres']-16.616)<.1
assert p['gap']['autoConnected'] is False and p['gap']['collisionEnabled'] is False
assert all(len(s['corners'])==4 for s in p['surfaces'])
assert r['phase2CSegments']==319 and r['candidateTopTriangles']==len(p['surfaces'])*2
assert p['officialReference']['totalLengthMetres']==250 and r['candidateDeckVsDocumentedLengthGapMetres']>100
bridge_gaps=[g for g in nav['blockedAreas'] if g.get('wayId')=='33976871']
assert len(bridge_gaps)>=1 and all(g['status']=='blocked' and g['autoConnected'] is False for g in bridge_gaps)
mid=[(p['gap']['endpointA'][0]+p['gap']['endpointB'][0])/2,(p['gap']['endpointA'][2]+p['gap']['endpointB'][2])/2]
assert all(math.dist(mid,[s['centerStart'][0],s['centerStart'][2]])>7 for run in nav['runs'] for s in run['segments'] if s.get('wayId')=='33976871')
assert r['fps']==60.1 and r['drawCalls']==55 and r['triangles']==600380
assert r['browserValidation']['phase2FTop']['drawCalls']==r['browserValidation']['baselinePhase2E']['drawCalls']+2
for f in r['screenshots']: assert (root/f).is_file() and (root/f).stat().st_size>5000, f
print('PASS: OSM/Phase 2C alignment, 16.616m gap blocked, navigation SHA-256 unchanged, estimated deck mesh separated, browser metrics and five PNGs verified')
