from pathlib import Path
import json, shutil, re, hashlib

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'build-phaseD1'
BUILD=ROOT/'build-phaseD11'
if not (SOURCE/'web/phaseD1/app.js').is_file(): raise SystemExit('Build Phase D1 first')
if BUILD.exists(): shutil.rmtree(BUILD)
shutil.copytree(SOURCE,BUILD)
web=BUILD/'web/phaseD1'; web.rename(BUILD/'web/phaseD11'); web=BUILD/'web/phaseD11'
shutil.copy2(ROOT/'scripts/phaseD11/bus-loader.js',web/'bus-loader.js')
html=(web/'index.html').read_text(encoding='utf-8')
html=html.replace('<title>KIBA PARK DRIVE · Phase D1</title>','<title>KIBA PARK DRIVE · Phase D1.1</title>')
html=html.replace('<label><input id="driveDebug" type="checkbox"> DEV車体・園路幅</label>', '<label><input id="driveDebug" type="checkbox"> DEV車体・園路幅・4輪接地</label><output id="contactDebug">タイヤ接地データを読込中</output>')
(web/'index.html').write_text(html,encoding='utf-8')
css=(web/'style.css').read_text(encoding='utf-8')+"\n#contactDebug{grid-column:1/-1;display:none;font:11px/1.5 ui-monospace,Consolas,monospace;color:#254a39;background:#dcebe0;border-radius:5px;padding:4px 6px;font-variant-numeric:tabular-nums}\n"
(web/'style.css').write_text(css,encoding='utf-8')
app=(web/'app.js').read_text(encoding='utf-8')
helper=(ROOT/'scripts/phaseD11/drive-contact-runtime.js').read_text(encoding='utf-8')
app=app.replace('function resetDrive(',helper+'\nfunction resetDrive(')
app=app.replace('driveCourse=(await response.json()).courses.A;driveWheelbase=driveCourse.busDimensionsMetres.wheelbase;', 'driveCourse=(await response.json()).courses.A;driveWheelbase=driveCourse.busDimensionsMetres.wheelbase;prepareDriveSupportSurface();')
app=app.replace("$('#driveDebug').addEventListener('change',e=>{if(driveWire)driveWire.visible=e.target.checked});", "$('#driveDebug').addEventListener('change',e=>{if(driveWire)driveWire.visible=e.target.checked;$('#contactDebug').style.display=e.target.checked?'block':'none';updateDriveContactHud()});")
app=app.replace("$('#cameraToggle').addEventListener('click',()=>{driveCamera=driveCamera==='chase'?'front':'chase'});", "$('#cameraToggle').addEventListener('click',()=>{driveCamera=driveCamera==='chase'?'above':'chase'});")
app=app.replace("$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?setDriveMode('battle'):setView('top')});", "$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?driveCamera='above':setView('top')});")
app=app.replace('/__phaseD1_screenshot__/', '/__phaseD11_screenshot__/')
app=app.replace("const names={top:'d1_overview.png',bridge:'d1_overview.png',side:'d1_overview.png',robot:driveMode==='drive'?(driveCamera==='chase'?'d1_drive_start.png':driveCamera==='above'?'d1_overview.png':'d1_drive_turn.png'):'d1_battle_mode.png',bus:driveCamera==='chase'?'d1_drive_start.png':driveCamera==='above'?'d1_overview.png':'d1_drive_turn.png'};", "const names={top:'d11_after_start.png',bridge:'d11_turnaround.png',side:'d11_midcourse.png',robot:driveMode==='drive'?'d11_after_start.png':'d11_after_start.png',bus:driveCoursePhase==='complete'?'d11_return.png':driveDistanceAlong>driveCourse.lengthMetres-5?'d11_turnaround.png':driveDistanceAlong>9?'d11_midcourse.png':'d11_after_start.png'};")
reset_new="""function resetDrive(){if(!bus||!driveCourse)return;driveSpeed=0;driveSteer=0;driveCoursePhase='outbound';const p=drivePointAt(2.8);driveDistanceAlong=2.8;const fit=fitBusToWheelSurfaces(p.x,p.z,p.heading);if(!fit.ok){driveLastReason=fit.reason;driveHud('接地データ不足 · 安全停止 · '+fit.reason);return}driveHeading=p.heading;driveBlocked=0;driveLastReason='';driveHud('Aコース · 4輪接地 · 発進できます')}"""
start=app.index('function resetDrive(');end=app.index('\nfunction driveCollisionTrees',start);app=app[:start]+reset_new+app[end:]
update_new="""function updateDrive(dt){if(!bus||driveMode!=='drive')return;const acc=keys.has('w')?2.0:0,brake=keys.has('s');if(acc)driveSpeed=Math.min(DRIVE_MAX_SPEED,driveSpeed+acc*dt);else if(brake){if(driveSpeed>.18)driveSpeed=Math.max(0,driveSpeed-4.2*dt);else driveSpeed=Math.max(-DRIVE_MAX_REVERSE,driveSpeed-1.25*dt)}else driveSpeed*=Math.max(0,1-.72*dt);const steerInput=(keys.has('d')?1:0)-(keys.has('a')?1:0);driveSteer=steerInput*driveMaxSteer;if(Math.abs(driveSpeed)>.005){const oldPos=bus.position.clone(),oldQuat=bus.quaternion.clone(),nextHeading=driveHeading+driveSpeed/driveWheelbase*Math.tan(driveSteer)*dt,forwardX=Math.sin((driveHeading+nextHeading)/2),forwardZ=Math.cos((driveHeading+nextHeading)/2),nx=bus.position.x+forwardX*driveSpeed*dt,nz=bus.position.z+forwardZ*driveSpeed*dt,q=driveProject(nx,nz),fit=driveFootprintCheck(nx,nz,nextHeading);let support={ok:false,reason:'路面接地点未計算'};if(fit.ok)support=fitBusToWheelSurfaces(nx,nz,nextHeading);if(Math.abs(q.grade)>DRIVE_MAX_GRADE){bus.position.copy(oldPos);bus.quaternion.copy(oldQuat);driveSpeed=0;driveBlocked++;driveLastReason='勾配超過 · 安全停止'}else if(!fit.ok||!support.ok){bus.position.copy(oldPos);bus.quaternion.copy(oldQuat);driveSpeed=0;driveBlocked++;driveLastReason=fit.ok?support.reason:fit.reason}else{driveHeading=nextHeading;driveDistanceAlong=q.station;driveLastReason='';if(driveCoursePhase==='outbound'&&q.station>=driveCourse.lengthMetres-2.9){driveCoursePhase='return';driveSpeed=0;driveHud('チェックポイント到着 · ブレーキ後、S長押しで後退')}if(driveCoursePhase==='return'&&q.station<=3.1&&Math.abs(driveSpeed)<.1){driveCoursePhase='complete';driveSpeed=0;driveHud('GOAL · Aコース往復完了 · Rで再走行')}}}else if(driveLastReason)driveHud(driveLastReason+' · 安全停止');if(driveCoursePhase==='outbound'&&driveDistanceAlong>=driveCourse.lengthMetres-2.8)driveHud('チェックポイント · Sでブレーキ、停止後S長押しで後退');else if(driveCoursePhase==='return'&&driveDistanceAlong<=3.1&&Math.abs(driveSpeed)<.1){driveCoursePhase='complete';driveHud('GOAL · Aコース往復完了 · Rで再走行')}else if(!driveLastReason)driveHud(driveCoursePhase==='complete'?'GOAL · Aコース往復完了 · Rで再走行':`安全走行 · ${driveCoursePhase==='outbound'?'OUT':'RETURN'} · route ${driveDistanceAlong.toFixed(1)}m`)}"""
start=app.index('function updateDrive(dt){');end=app.index('\nfunction render(data,nav,veg){',start);app=app[:start]+update_new+app[end:]
(web/'app.js').write_text(app,encoding='utf-8')

before=ROOT/'screenshots/phaseD1'; shots=ROOT/'screenshots/phaseD11'; shots.mkdir(parents=True,exist_ok=True)
for src,name in [(before/'d1_drive_start.png','d11_before.png'),(before/'d1_overview.png','d11_before_overview.png')]:
 if src.is_file():shutil.copy2(src,shots/name)
inspection=json.loads((ROOT/'reports/phaseD1/tayo_model_inspection.json').read_text(encoding='utf-8'))
gltf=(web/'tayo_bus_phaseD1.glb').read_bytes()
report={'phase':'KIBA PARK DRIVE Phase D1.1','sourceD1Sha256':hashlib.sha256((SOURCE/'web/phaseD1/app.js').read_bytes()).hexdigest(),'glbSha256':hashlib.sha256(gltf).hexdigest(),'originalBlendSha256':inspection['sourceSha256'],'sourceBlendReadOnly':True,'terrainAndRoadElevationsModified':False,'contactMethod':'For each frame, sample the actual two-triangle OSM A-course road surface at the four GLB-derived tire contact points; fit bus pitch, roll, and vertical position to those four heights. DEM grid height is also recorded for comparison.','clearanceMetres':0.012,'wheelbaseMetres':inspection['wheelbaseMetres'],'wheelTrackMetres':inspection['trackWidthBetweenWheelCentersMetres'],'glbBoundsAndWheelContacts':'Recorded at runtime in bus-loader userData from the transformed GLB scene graph.'}
(ROOT/'reports/phaseD11/contact_method.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Built Phase D1.1 separately:',web)
print('A-road support triangles:',len(json.loads((SOURCE/'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))['roads'][next(i for i,r in enumerate(json.loads((SOURCE/'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))['roads']) if str(r['id'])=='777288664')]['indices'])//3)
