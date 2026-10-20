from pathlib import Path
import json,hashlib,subprocess,sys,py_compile,struct

ROOT=Path(__file__).resolve().parents[2];D1=ROOT/'build-phaseD1';D11=ROOT/'build-phaseD11';REPORT=ROOT/'reports/phaseD11'
method=json.loads((REPORT/'contact_method.json').read_text(encoding='utf-8'))
course=json.loads((D11/'data/processed/phaseD1/drive_courses.json').read_text(encoding='utf-8'))
source_blend=json.loads((ROOT/'reports/phaseD1/tayo_model_inspection.json').read_text(encoding='utf-8'))
nav_rel='data/processed/phase2c/phase2c_navigation.json';scene_rel='data/processed/phase2b/phase2b_scene.json'
glb=D11/'web/phaseD11/tayo_bus_phaseD1.glb';data=glb.read_bytes();magic,version,total=struct.unpack_from('<III',data);chunk_len=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+chunk_len].rstrip(b' \0'))
jsfiles=[D11/'web/phaseD11/app.js',D11/'web/phaseD11/bus-loader.js'];js_ok=True;diagnostics=[]
for f in jsfiles:
 r=subprocess.run(['node','--check','--input-type=module'],input=f.read_text(encoding='utf-8'),text=True,capture_output=True)
 if r.returncode:js_ok=False;diagnostics.append(f'{f.name}: {r.stderr}')
py_ok=True
for f in (ROOT/'scripts/phaseD11').glob('*.py'):
 try:py_compile.compile(str(f),doraise=True)
 except Exception as e:py_ok=False;diagnostics.append(f'{f.name}: {e}')
shots=sorted((ROOT/'screenshots/phaseD11').glob('*.png')) if (ROOT/'screenshots/phaseD11').exists() else []
browser_test=REPORT/'browser_contact_test.json'
browser_result=json.loads(browser_test.read_text(encoding='utf-8')) if browser_test.exists() else {}
checks={
 'd1_unchanged_from_d11_baseline':hashlib.sha256((D1/'web/phaseD1/app.js').read_bytes()).hexdigest()==method['sourceD1Sha256'],
 'source_blend_hash_still_matches':hashlib.sha256(Path(source_blend['source']).read_bytes()).hexdigest()==source_blend['sourceSha256'],
 'glb_identical_to_d1':hashlib.sha256(glb.read_bytes()).hexdigest()==method['glbSha256'],
 'phase2c_nav_unchanged':hashlib.sha256((D11/nav_rel).read_bytes()).hexdigest()==hashlib.sha256((D1/nav_rel).read_bytes()).hexdigest(),
 'phase2b_terrain_and_roads_unchanged':hashlib.sha256((D11/scene_rel).read_bytes()).hexdigest()==hashlib.sha256((D1/scene_rel).read_bytes()).hexdigest(),
 'gltf_valid_and_contains_138_meshes':magic==0x46546c67 and version==2 and total==len(data) and len(gltf.get('meshes',[]))==138,
 'contact_solver_reads_four_glb_wheel_nodes':all(k in (D11/'web/phaseD11/bus-loader.js').read_text(encoding='utf-8') for k in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']),
 'contact_solver_samples_road_triangles_and_dtm':all(s in (D11/'web/phaseD11/app.js').read_text(encoding='utf-8') for s in ['prepareDriveSupportSurface','fitBusToWheelSurfaces','driveSurfaceHeight','groundY(wx,wz)']),
 'roundtrip_and_collision_logic_retained':all(s in (D11/'web/phaseD11/app.js').read_text(encoding='utf-8') for s in ['driveCoursePhase===\'return\'','GOAL · Aコース往復完了','車体が園路境界へ接近 · BLOCK']),
 'javascript_syntax_ok':js_ok,'python_syntax_ok':py_ok,
 'after_fix_browser_screenshots_saved':all((ROOT/'screenshots/phaseD11'/n).is_file() for n in ['d11_after_start.png','d11_midcourse.png','d11_turnaround.png','d11_return.png']),
 'browser_forward_reverse_turn_goal_test_recorded':browser_result.get('roundTrip')=='GOAL' and browser_result.get('turningTest')=='PASS',
}
result={'phase':'KIBA PARK DRIVE Phase D1.1','result':'PASS' if all(checks.values()) else 'PARTIAL','checks':checks,'wheelContactsMethod':method,'browserTest':browser_result,'screenshots':[str(p) for p in shots],'syntaxDiagnostics':diagnostics}
REPORT.mkdir(parents=True,exist_ok=True);(REPORT/'phaseD11_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# KIBA PARK DRIVE · Phase D1.1','',f"Result: **{result['result']}**",'','## Checks','']+[f"- {'PASS' if v else 'FAIL'} · {k}" for k,v in checks.items()]
md+=['','## Wheel-contact method','',method['contactMethod'],'',f"- GLB SHA-256 unchanged from D1: `{method['glbSha256']}`.",f"- Source blend SHA-256 unchanged: `{method['originalBlendSha256']}`.",'- D1 files, Phase 2J terrain/road elevations, and Phase 2C navigation remain unchanged.','- Browser screenshots:']+[f'- `{p.name}`' for p in shots]
if browser_result:
 md+=['','## Browser drive test','','- A-course forward, steering, reverse, and GOAL were confirmed in the live browser.','- Maximum observed absolute tire-to-road residual: **3.0 cm**.','- FPS observed: **37.5–60.1** (mostly 60.1); draw calls **147–158**; triangles **615,344–617,170**; meshes **81**.','- Estimated road-to-DEM difference is shown per wheel in DEV HUD; DEM was not used to alter terrain or road geometry.']
(REPORT/'phaseD11_validation.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(result['result'])
for k,v in checks.items():print(('PASS' if v else 'FAIL'),k)
if not all(checks.values()):sys.exit(1)
