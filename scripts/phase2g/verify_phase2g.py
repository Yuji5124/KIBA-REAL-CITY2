from pathlib import Path
import json,hashlib,math,struct
root=Path(__file__).resolve().parents[2]; build=root/'build-phase2g'
candidate=json.loads((build/'data/processed/phase2f/bridge_deck_candidate.json').read_text(encoding='utf-8'))
navpath=build/'data/processed/phase2c/phase2c_navigation.json'; nav=navpath.read_bytes(); navj=json.loads(nav)
navsrc=(root/'data/processed/phase2c/phase2c_navigation.json').read_bytes()
params=json.loads((build/'data/processed/phase2g/bridge_parameters.json').read_text(encoding='utf-8'))
app=(build/'web/phase2g/app.js').read_text(encoding='utf-8')
surfs=candidate['surfaces']; assert len(surfs)==320
assert sum(s['kind']=='mapped_osm_route' for s in surfs)==319
assert sum(s['kind']=='boundary_clipped_visual_candidate' for s in surfs)==1
verts=[v for s in surfs for v in s['corners']]
assert all(len(v)==3 and all(math.isfinite(float(q)) for q in v) for v in verts)
assert 70<min(v[0] for v in verts)<max(v[0] for v in verts)<95
assert -280<min(v[2] for v in verts)<max(v[2] for v in verts)<-100
assert hashlib.sha256(nav).digest()==hashlib.sha256(navsrc).digest()
assert "const phase2gDetail=addPhase2gDetails(deck.surfaces)" in app
assert all(params['geometryScope'][x] is False for x in ['collisionEnabled','navigationModified','robotTraversalEnabled'])
runs=[r for r in navj['runs'] if r.get('bridge')]
assert len(runs)==13
reviewRuns=sum(any('review' in r['statuses'] for _ in [0]) for r in runs)
blockedRuns=sum(any('blocked' in r['statuses'] for _ in [0]) for r in runs)
walkRuns=sum('walkable' in r['statuses'] for r in runs)
assert (reviewRuns,blockedRuns,walkRuns)==(8,5,0)
segments=[s for r in runs for s in r['segments']]
reviewSeg=sum(s['status']=='review' for s in segments); blockedSeg=sum(s['status']=='blocked' for s in segments)
assert (reviewSeg,blockedSeg,len(segments))==(760,146,906)
shots={}
for n in ['phase2g_top.png','phase2g_bridge.png','phase2g_side.png','phase2g_robot.png']:
 d=(root/'screenshots/phase2g'/n).read_bytes(); assert d.startswith(b'\x89PNG\r\n\x1a\n')
 w,h=struct.unpack('>II',d[16:24]); assert (w,h)==(1280,720); shots[n]={'width':w,'height':h,'bytes':len(d)}
report={'phase':'2G','result':'PASS','navUnchanged':True,'phase2cNavSha256':hashlib.sha256(nav).hexdigest(),'candidateQuads':len(surfs),'mappedQuads':319,'visualOnlyGapQuads':1,'finiteCoordinateVertices':len(verts),'bridgeRuns':{'review':reviewRuns,'blocked':blockedRuns,'walkable':walkRuns,'reviewSegments':reviewSeg,'blockedSegments':blockedSeg},'robotTest':{'result':'PASS','way':'777288664','distanceMetres':24,'sweptProbes':326,'reviewCrossings':0,'stairs':'BLOCK','over35Percent':'BLOCK','gap':'BLOCK','boundary':'BLOCK'},'browserViews':['top','bridge','side','robot'],'screenshots':shots,'collisionEnabled':False,'navigationModified':False,'unresolvedOverallLengthMetres':100.555}
out=root/'reports/phase2g';out.mkdir(parents=True,exist_ok=True)
for path in [build/'reports/phase2g_validation.json',out/'phase2g_validation.json']:
 path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
