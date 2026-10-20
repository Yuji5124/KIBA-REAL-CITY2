from pathlib import Path
import json, math, struct, subprocess, sys, hashlib, py_compile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'build-phase2j/data/processed'
D1=ROOT/'build-phaseD1'
REPORT=ROOT/'reports/phaseD1'
course=json.loads((D1/'data/processed/phaseD1/drive_courses.json').read_text(encoding='utf-8'))
scene=json.loads((SOURCE/'phase2b/phase2b_scene.json').read_text(encoding='utf-8'))
nav=json.loads((SOURCE/'phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))
veg=json.loads((SOURCE/'phase2d/phase2d_vegetation.json').read_text(encoding='utf-8'))
insp=json.loads((REPORT/'tayo_model_inspection.json').read_text(encoding='utf-8'))
blend_source=Path(insp['source'])
actual_blend_sha=hashlib.sha256(blend_source.read_bytes()).hexdigest() if blend_source.is_file() else None
A=course['courses']['A']; pts=A['points']; L=A['routeLengthMetres']; half=A['roadWidthMetres']/2
path=[(p[0],p[2],p[1]) for p in pts]
def sample(s):
    rem=max(0.,min(L,s))
    for a,b in zip(path,path[1:]):
        d=math.hypot(b[0]-a[0],b[1]-a[1])
        if rem<=d:
            t=rem/d if d else 0
            return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t)
        rem-=d
    return path[-1]
def project(x,z):
    best=(math.inf,0,0.,0.); station=0.
    for a,b in zip(path,path[1:]):
        dx=b[0]-a[0]; dz=b[1]-a[1]; d=math.hypot(dx,dz); l2=d*d
        t=max(0.,min(1.,((x-a[0])*dx+(z-a[1])*dz)/l2 if l2 else 0.))
        distance=math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)
        if distance<best[0]:best=(distance,station+t*d,a[2]+t*(b[2]-a[2]),abs((b[2]-a[2])/d) if d else 0.)
        station+=d
    return best
def point_poly(p,poly):
    x,z=p; inside=False
    for i in range(len(poly)):
        a=poly[i];b=poly[i-1]
        if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside
def in_obb(px,pz,x,z,h):
    dx=px-x;dz=pz-z;long=dx*math.sin(h)+dz*math.cos(h);lat=dx*math.cos(h)-dz*math.sin(h)
    return abs(long)<=2.26 and abs(lat)<=1.36
max_corner=0.;min_remaining=math.inf;max_grade=0.;bad_nav=[];tree_hits=[];polygon_hits=[]
alltrees=veg.get('mappedTrees',[])+veg.get('estimatedTrees',[])
polys=[]
for f in scene['features'].get('water',[])+scene['features'].get('buildings',[]):
    poly=[[p[0],p[2]] for p in f.get('points',[])]
    if len(poly)>=3:polys.append(poly)
for s in [i/4 for i in range(12, math.floor((L-2.8)*4)+1)]:
    x,z,y=sample(s); before=sample(max(0,s-.15)); after=sample(min(L,s+.15));h=math.atan2(after[0]-before[0],after[1]-before[1]);grade=abs((after[2]-before[2])/max(1e-9,math.hypot(after[0]-before[0],after[1]-before[1])));max_grade=max(max_grade,grade)
    corners=[]
    for lo in [-2.26,0,2.26]:
        for la in [-1.36,0,1.36]:
            px=x+math.sin(h)*lo+math.cos(h)*la;pz=z+math.cos(h)*lo-math.sin(h)*la
            dist,station,_,g=project(px,pz);max_corner=max(max_corner,dist);min_remaining=min(min_remaining,half-.12-dist)
            if station<-.08 or station>L+.08 or dist>half-.12:bad_nav.append({'station':round(s,2),'offset':round(dist,3),'reason':'outside estimated road envelope'})
            if g>.12:bad_nav.append({'station':round(s,2),'grade':round(g,4),'reason':'grade >12%'})
            corners.append([px,pz])
    if any(point_poly(c,p) for c in corners for p in polys) or any(point_poly([x,z],p) for p in polys):polygon_hits.append(round(s,2))
    for t in alltrees:
        dx=t['x']-x;dz=t['z']-z;long=dx*math.sin(h)+dz*math.cos(h);lat=dx*math.cos(h)-dz*math.sin(h)
        if abs(long)<2.5 and abs(lat)<1.6:tree_hits.append({'station':round(s,2),'tree':t.get('id')})
run=next(r for r in nav['runs'] if str(r['id'])==str(A['wayId']))
bridges=[r for r in nav['runs'] if r.get('bridge')]
bridge_walkable=sum(s['status']=='walkable' for r in bridges for s in r.get('segments',[]))
route_hash=hashlib.sha256((SOURCE/'phase2c/phase2c_navigation.json').read_bytes()).hexdigest()
d1nav_hash=hashlib.sha256((D1/'data/processed/phase2c/phase2c_navigation.json').read_bytes()).hexdigest()
phase3nav_hash=hashlib.sha256((ROOT/'build-phase3a/data/processed/phase2c/phase2c_navigation.json').read_bytes()).hexdigest()
glb=D1/'web/phaseD1/tayo_bus_phaseD1.glb'; data=glb.read_bytes(); magic,version,total=struct.unpack_from('<III',data); json_len,chunk=struct.unpack_from('<II',data,12); gltf=json.loads(data[20:20+json_len].rstrip(b' \0'))
jsfiles=[D1/'web/phaseD1/app.js',D1/'web/phaseD1/bus-loader.js']
node_ok=True;node_err=''
for f in jsfiles:
    r=subprocess.run(['node','--check','--input-type=module'],input=f.read_text(encoding='utf-8'),text=True,capture_output=True)
    if r.returncode:node_ok=False;node_err+=f'{f.name}: {r.stderr}\n'
py_ok=True
for f in (ROOT/'scripts/phaseD1').glob('*.py'):
    try:py_compile.compile(str(f),doraise=True)
    except Exception as e:py_ok=False;node_err+=f'{f.name}: {e}\n'
checks={
 'source_blend_hash_matches_read_only_inspection':actual_blend_sha==insp.get('sourceSha256'),
 'source_blend_read_only_flag':insp.get('readOnly') is True,
 'separate_gltf_exists_and_header_valid':magic==0x46546c67 and version==2 and total==len(data),
 'gltf_mesh_count_matches_inspection':len(gltf.get('meshes',[]))==insp['meshObjectCount'],
 'phase3a_copied_into_separate_d1':(D1/'web/phaseD1/app.js').exists() and (ROOT/'build-phase3a/web/phase3a/app.js').exists(),
 'course_a_24m_and_same_road':abs(L-24)<.1 and str(A['wayId'])=='777288664',
 'course_a_nav_walkable_only':A['navigationSegmentStatuses'].get('review',0)==0 and A['navigationSegmentStatuses'].get('blocked',0)==0,
 'course_a_not_bridge_or_stairs':A['bridge'] is False and A['stairs'] is False,
 'swept_body_inside_modeled_path':not bad_nav and min_remaining>0,
 'swept_body_avoids_tree_trunks':not tree_hits,
 'swept_body_avoids_osm_water_and_buildings':not polygon_hits,
 'max_course_grade_below_12pct':max_grade<.12,
 'all_bridge_run_nav_still_has_zero_walkable':len(bridges)==13 and bridge_walkable==0,
 'phase2c_nav_data_matches_source_and_phase3a':route_hash==d1nav_hash==phase3nav_hash,
 'javascript_syntax_ok':node_ok,
 'python_syntax_ok':py_ok,
}
browser_screens=sorted((ROOT/'screenshots/phaseD1').glob('*.png')) if (ROOT/'screenshots/phaseD1').exists() else []
checks['browser_screenshot_saved']=len(browser_screens)>=3
result={'phase':'KIBA PARK DRIVE Phase D1','result':'PASS' if all(checks.values()) else 'PARTIAL','checks':checks,'courseA':{'wayId':A['wayId'],'lengthMetres':L,'modeledWidthMetres':A['roadWidthMetres'],'busEnvelopeMetres':[A['busDimensionsMetres']['widthIncludingMirrors'],A['busDimensionsMetres']['length']],'sampledMinimumPlanRadiusMetres':A['minimumSampledPlanCurvatureRadiusMetres'],'maxGradeFraction':max_grade,'steeringAngleRequiredEstimateDegrees':math.degrees(math.atan(A['busDimensionsMetres']['wheelbase']/A['minimumSampledPlanCurvatureRadiusMetres'])),'steeringLimitPrototypeDegrees':16,'minSampledLateralReserveMetres':min_remaining,'maxCornerDistanceFromCenterlineMetres':max_corner,'treeHits':tree_hits[:8],'buildingWaterHits':polygon_hits,'uncertainNavigationPositions':bad_nav[:12],'unverifiedCandidateRoadRunReviewCount':sum(s['status']=='review' for s in run['segments'])},'phase2c':{'navSha256Source':route_hash,'navSha256D1':d1nav_hash,'navSha256Phase3A':phase3nav_hash,'bridgeRuns':len(bridges),'bridgeWalkableSegments':bridge_walkable},'glb':{'bytes':len(data),'meshCount':len(gltf.get('meshes',[])),'materials':len(gltf.get('materials',[]))},'browserScreenshots':[str(p) for p in browser_screens],'syntaxDiagnostics':node_err}
REPORT.mkdir(parents=True,exist_ok=True)
(REPORT/'phaseD1_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# KIBA PARK DRIVE · Phase D1 validation','',f"Result: **{result['result']}**",'', '## Checks','']
md += [f"- {'PASS' if v else 'FAIL'} · {k}" for k,v in checks.items()]
md += ['', '## Course A measured/modelled values','',f"- OSM way {A['wayId']}; {L:.2f}m route; modeled width {A['roadWidthMetres']:.3f}m (inferred, unsurveyed).",f"- Tayo envelope {A['busDimensionsMetres']['widthIncludingMirrors']:.2f}m wide × {A['busDimensionsMetres']['length']:.2f}m long; measured model wheelbase {A['busDimensionsMetres']['wheelbase']:.2f}m; forward axis Blender −Y.",f"- Sampled plan radius ≥{A['minimumSampledPlanCurvatureRadiusMetres']:.2f}m; estimated steering need {result['courseA']['steeringAngleRequiredEstimateDegrees']:.1f}° versus prototype max 16°.",f"- 2D swept-body lateral reserve in the modeled corridor: {min_remaining:.3f}m; maximum sampled terrain grade {max_grade*100:.2f}%.",'- The clearance is computed from a Phase 2B inferred road width, not an on-site measurement; the route is a gameplay prototype, not real-world access approval.','', '## Mode separation','',f"- Bridge navigation remains {len(bridges)} runs and {bridge_walkable} walkable bridge segments.",'- The Phase 3A battle mode remains copied into D1 and uses its existing Phase 2C navigation; D1 driving is restricted to A test course.','', '## Incomplete','', '- B/C remain disabled. Their candidate ways have narrower modeled widths or review segments; no whole-vehicle swept-envelope validation has been performed.', '- Tayo asset contains no steering-angle or turning-radius specification; runtime steering is an explicitly estimated prototype parameter.', '- Browser and screenshot checks complete after playtest; performance figures must be sampled live in the same viewport.','']
(REPORT/'phaseD1_validation.md').write_text('\n'.join(md),encoding='utf-8')
print(result['result'])
for k,v in checks.items():print(('PASS' if v else 'FAIL'),k)
print('min lateral reserve',round(min_remaining,3),'m; grade max',round(max_grade*100,2),'%; curvature',A['minimumSampledPlanCurvatureRadiusMetres'],'m')
if not all(checks.values()):sys.exit(1)
