import json, math, sys, collections
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'data/processed/phase2d/phase2d_vegetation.json').is_file())
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
data = json.loads((ROOT / 'data/processed/phase2d/phase2d_vegetation.json').read_text(encoding='utf-8'))
report = json.loads((ROOT / 'reports/phase2d/phase2d_source_analysis.json').read_text(encoding='utf-8'))
scene = json.loads((SRC / 'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))
nav = json.loads((SRC / 'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))

def inside(x,z,ring):
    c=False;j=len(ring)-1
    for i,(xx,zz) in enumerate(ring):
        xj,zj=ring[j]
        if (zz>z)!=(zj>z) and x<(xj-xx)*(z-zz)/(zj-zz+1e-30)+xx:c=not c
        j=i
    return c
def inside_any(x,z,rings):return any(inside(x,z,r) for r in rings if len(r)>=3)
def dist_seg(px,pz,ax,az,bx,bz):
    dx,dz=bx-ax,bz-az;t=max(0,min(1,((px-ax)*dx+(pz-az)*dz)/(dx*dx+dz*dz+1e-12)));return math.hypot(px-ax-t*dx,pz-az-t*dz)
park=[[ (p[0],p[2]) for p in ring] for ring in scene['parkBoundary']]
water=[[(p[0],p[2]) for p in f.get('points',[])] for f in scene['features']['water'] if len(f.get('points',[]))>=3]
buildings=[[(p[0],p[2]) for p in f.get('points',[])] for f in scene['features']['buildings'] if len(f.get('points',[]))>=3]
roads=[]
road_bins=collections.defaultdict(list); cell=8.0
for run in nav['runs']:
    for s in run['segments']:
        r=(s['centerStart'][0],s['centerStart'][2],s['centerEnd'][0],s['centerEnd'][2],s['widthMetres']/2+.55);roads.append(r)
        for ix in range(math.floor((min(r[0],r[2])-r[4])/cell),math.floor((max(r[0],r[2])+r[4])/cell)+1):
            for iz in range(math.floor((min(r[1],r[3])-r[4])/cell),math.floor((max(r[1],r[3])+r[4])/cell)+1):road_bins[(ix,iz)].append(r)
records=data['mappedTrees']+data['estimatedTrees']+data['estimatedShrubs']+data['grassTufts']
bad={'outsidePark':0,'water':0,'building':0,'pathBridgeClearance':0}
for q in records:
    x,z=q['x'],q['z']
    if not inside_any(x,z,park):bad['outsidePark']+=1
    if inside_any(x,z,water):bad['water']+=1
    if inside_any(x,z,buildings):bad['building']+=1
    if any(dist_seg(x,z,*r[:4])<r[4] for r in road_bins.get((math.floor(x/cell),math.floor(z/cell)),[])):bad['pathBridgeClearance']+=1
assert len(data['mappedTrees']) == 42
assert data['sourceCounts']['phase2bVegetationFeatures'] == 48
assert data['sourceCounts']['osmVegetationAreasUsed'] == 5
assert sum(q['source']=='estimated_from_aerial_canopy' for q in data['estimatedTrees']) > 0
assert sum(q['source']=='estimated_from_osm_vegetation_area' for q in data['estimatedTrees']) > 0
assert data['photoCoverage']['tileCount'] == 14
assert 0 < data['photoCoverage']['coveredParkPercent'] < 100
assert data['photoCoverage']['treePointCoverageCount'] == 0
assert not any(bad.values()), bad
assert report['rawInputsModified'] is False and report['render']['terrainChanged'] is False and report['render']['movementLayerChanged'] is False
assert len(data['vegetationAreas']) == 5 and len(data['photoCoverage']['tiles']) == 14
print(json.dumps({'result':'PASS','sourceCounts':data['sourceCounts'],'photoCoveragePercent':data['photoCoverage']['coveredParkPercent'],'exclusionViolations':bad,'phase2cTestRouteMetres':nav['testRoute']['lengthMetres']},ensure_ascii=False,indent=2))
