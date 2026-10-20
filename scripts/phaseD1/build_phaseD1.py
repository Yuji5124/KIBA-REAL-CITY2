from pathlib import Path
import json, math, shutil, hashlib

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'build-phase3a'
BUILD=ROOT/'build-phaseD1'
if not SOURCE.is_dir(): raise SystemExit('Phase 2J build missing')
if BUILD.exists(): shutil.rmtree(BUILD)
shutil.copytree(SOURCE,BUILD)
web=BUILD/'web/phase3a'; web.rename(BUILD/'web/phaseD1'); web=BUILD/'web/phaseD1'

scene=json.loads((SOURCE/'data/processed/phase2b/phase2b_scene.json').read_text(encoding='utf-8'))
nav=json.loads((SOURCE/'data/processed/phase2c/phase2c_navigation.json').read_text(encoding='utf-8'))
veg=json.loads((SOURCE/'data/processed/phase2d/phase2d_vegetation.json').read_text(encoding='utf-8'))
inspection=json.loads((ROOT/'reports/phaseD1/tayo_model_inspection.json').read_text(encoding='utf-8'))
asset=ROOT/'assets/phaseD1/tayo_bus_phaseD1.glb'
if not asset.is_file(): raise SystemExit('Run inspect_tayo.py first to create the clone-side GLB')
route=nav['testRoute']
if str(route['wayId'])!='777288664' or abs(float(route['lengthMetres'])-24)>1e-6: raise SystemExit('Expected preserved 24m way 777288664 course segment')
road=next(r for r in scene['roads'] if str(r['id'])=='777288664')
run=next(r for r in nav['runs'] if str(r['id'])=='777288664')
segments=run['segments']
points=route['points']
length=sum(math.hypot(b[0]-a[0],b[2]-a[2]) for a,b in zip(points,points[1:]))
def nearest_seg(x,z):
    best=(math.inf,None)
    for s in segments:
        a=s['centerStart'];b=s['centerEnd'];dx=b[0]-a[0];dz=b[2]-a[2];l2=dx*dx+dz*dz;t=max(0.,min(1.,((x-a[0])*dx+(z-a[2])*dz)/l2 if l2 else 0.));dist=math.hypot(x-a[0]-t*dx,z-a[2]-t*dz)
        if dist<best[0]:best=(dist,s)
    return best
course_segments=[]
for a,b in zip(points,points[1:]):
    for t in (0,.5,1):
        d,s=nearest_seg(a[0]+(b[0]-a[0])*t,a[2]+(b[2]-a[2])*t)
        if d>.25 or not s or s['status']!='walkable': raise SystemExit('Course A contains unverified nav surface')
        if s not in course_segments:course_segments.append(s)
grades=[abs((b[1]-a[1])/math.hypot(b[0]-a[0],b[2]-a[2])) for a,b in zip(points,points[1:]) if math.hypot(b[0]-a[0],b[2]-a[2])>0]
if any(g>.12 for g in grades):raise SystemExit('Course A exceeds prototype grade limit')
path2d=[(p[0],p[2]) for p in points]
radius=[]
for i in range(1,len(path2d)-1):
    a=(path2d[i][0]-path2d[i-1][0],path2d[i][1]-path2d[i-1][1]); b=(path2d[i+1][0]-path2d[i][0],path2d[i+1][1]-path2d[i][1])
    la=math.hypot(*a); lb=math.hypot(*b); c=(path2d[i+1][0]-path2d[i-1][0],path2d[i+1][1]-path2d[i-1][1]); chord=math.hypot(*c); cross=abs(a[0]*b[1]-a[1]*b[0])
    if cross>1e-9: radius.append(la*lb*chord/(2*cross))
min_radius=min(radius) if radius else None
width=min(float(s['widthMetres']) for s in course_segments)
bus_width=float(inspection['worldDimensionsXYZ'][0]); bus_length=float(inspection['worldDimensionsXYZ'][1]); wheelbase=float(inspection['wheelbaseMetres'])
margin=(width-bus_width)/2
course={
 'phase':'D1','crs':'EPSG:6677','coordinateConvention':scene['coordinateConvention'],'source':'Phase 2J copied datasets; read only','courses':{
  'A':{'title':'はじめてドライブ','status':'playable-prototype-candidate','wayId':'777288664','sourceRun':run['run'],'routeLengthMetres':length,'lengthMetres':length,'points':points,'roadWidthMetres':width,'roadWidthBasis':'Phase 2B inferred drive/service-road width; not surveyed','navigationSegmentStatuses':{s:sum(q['status']==s for q in course_segments) for s in ['walkable','review','blocked']},'bridge':False,'stairs':False,'maxNavigationGradeFraction':max(grades or [0]),'minimumSampledPlanCurvatureRadiusMetres':min_radius,'busDimensionsMetres':{'widthIncludingMirrors':bus_width,'length':bus_length,'height':float(inspection['worldDimensionsXYZ'][2]),'wheelbase':wheelbase,'trackWidth':float(inspection['trackWidthBetweenWheelCentersMetres'])},'nominalClearancePerSideMetres':margin,'clearanceInterpretation':'Only 4m modeled corridor minus 2.72m model envelope, before additional operational margin; collision runtime uses the modeled road envelope and blocks uncertain nav areas. Candidate use only; width not surveyed.','roundTrip':'Drive to far checkpoint, brake, reverse along same validated ribbon, return to start. No bridge routes.'},
  'B':{'title':'もりのたんけん','status':'candidate-unverified','candidateWayIds':['742189607','749128168'],'lengthMetres':984.23,'widthMetres':3.6,'reason':'Long woodland-adjacent path candidate, but width is an inferred 3.6m class and 749128168 has review sections. Bus footprint sweeps and vegetation/obstacle clearance not run; not driveable in D1.'},
  'C':{'title':'こうえんツアー','status':'candidate-unverified','candidateWayIds':['777288663','683394372'],'lengthMetres':[196.39,283.58],'widthMetres':[4.0,3.6],'reason':'Potential service-road/plaza and park-path itinerary; 777288663 has review portions, and all bridge/13 run areas remain blocked. No inter-run vehicle connectivity validation; not driveable in D1.'}
 },'vehicleModel':{'sourceBlendReadOnly':inspection['source'],'glb':'tayo_bus_phaseD1.glb','blenderVersion':inspection['blenderVersion'],'sourceSha256':inspection['sourceSha256'],'blendUnits':inspection['sceneUnitSystem'],'scaleLength':inspection['scaleLength'],'forwardAxisInBlender':inspection['forwardAxis'],'bodyBoundsBlenderXYZMetres':inspection['worldDimensionsXYZ'],'wheelbaseMetres':wheelbase,'frontAxleCenter':inspection['frontAxleCenterWorld'],'rearAxleCenter':inspection['rearAxleCenterWorld'],'turningRadius':'Not authored in model; runtime steering is a conservative bicycle-model estimate (max steer 16°), not a certified vehicle specification.'},
 'verificationPolicy':{'experimentalVehicleCorridorOnly':True,'phase2cNavigationModified':False,'bridgesDriveable':False,'maxDriveGradeFraction':0.12,'bodyFootprintSwept':True,'treesBuildingsWaterChecked':True,'allUncertainAreasStop':True,'limitations':['OSM-derived modeled path widths are not a site survey.','The 24m Phase 2C test route is a limited local candidate, not proof of public vehicle access.','The original Tayo asset has no authored steering geometry or turning-radius specification.']}}
out=BUILD/'data/processed/phaseD1'; out.mkdir(parents=True,exist_ok=True)
(out/'drive_courses.json').write_text(json.dumps(course,ensure_ascii=False,indent=2),encoding='utf-8')
asset_copy=web/'tayo_bus_phaseD1.glb'; shutil.copy2(asset,asset_copy)
shutil.copy2(ROOT/'scripts/phaseD1/bus-loader.js',web/'bus-loader.js')
html=(web/'index.html').read_text(encoding='utf-8')
html=html.replace('<title>KIBA PARK · Phase 3A</title>','<title>KIBA PARK DRIVE · Phase D1</title>')
html=html.replace('木場公園 · Phase 3A ロボットアクション','木場公園 · Tayoバスでドライブ')
html=html.replace('<button id="viewRobot">ゲームカメラ</button><button id="viewAbove">上空視点</button><button id="test">既存24m移動テスト</button><button id="attack">攻撃（Space / J）</button><button id="restart">再開（R）</button><button id="saveShot">画面を保存</button>', '<button id="modeDrive">🚌 ドライブ</button><button id="modeBattle">🤖 ロボット戦闘</button><button id="viewRobot">追従カメラ</button><button id="viewAbove">上空視点</button><button id="cameraToggle">カメラ C</button><button id="test">24m検証</button><button id="attack">攻撃（Space / J）</button><button id="restart">R コース再開</button><button id="saveShot">画面を保存</button>')
html=html.replace('操作: WASDで移動 · Space / Jで攻撃 · 園路上で敵1体を撃破','W アクセル · S ブレーキ / 後退 · A/D ハンドル · C カメラ · R スタートへ戻る')
html=html.replace('<small>W アクセル','<small id="controlsHint">W アクセル')
html=html.replace('<output id="gameStatus">','<output id="driveStatus">Tayoバス GLB 読込中…</output><output id="gameStatus">')
html=html.replace('<div id="health">','<div id="vehicleHud"><b id="speedDisplay">0.0 km/h</b><span id="courseDisplay">A · はじめてドライブ</span><span id="checkpointDisplay">コース読込中</span><label><input id="driveDebug" type="checkbox"> DEV車体・園路幅</label><select id="courseSelect"><option value="A">A · はじめてドライブ</option><option value="B" disabled>B · もりのたんけん（未検証）</option><option value="C" disabled>C · こうえんツアー（未検証）</option></select></div><div id="health">')
html=html.replace('<span><i class="walk"></i>移動可能</span>','<span><i class="driveable"></i>仮運転可能（A試験路）</span><span><i class="walk"></i>歩行ナビ</span>')
(web/'index.html').write_text(html,encoding='utf-8')
css=(web/'style.css').read_text(encoding='utf-8')+"\n#vehicleHud{display:grid;grid-template-columns:1fr 1fr;gap:5px;align-items:center;padding:7px 9px;border-radius:8px;background:#edf4ef;color:#294638}#vehicleHud b{font-size:18px;font-variant-numeric:tabular-nums;color:#12624b}#vehicleHud label{grid-column:1/-1}#courseSelect{padding:5px;border:1px solid #acc0b4;border-radius:5px;background:white;color:#293a31}#driveStatus{padding:6px 8px;border-radius:7px;background:#e9f4eb;color:#244d35;font-weight:650}#legend .driveable{background:#ffd34f;border:1px solid #8c6d00}#modeDrive.active,#modeBattle.active{background:#e2a632;color:#273523}#debug,#deckToggle{display:none}\n"
(web/'style.css').write_text(css,encoding='utf-8')
app=(web/'app.js').read_text(encoding='utf-8')
app=app.replace("import * as THREE from './vendor/three.module.js';", "import * as THREE from './vendor/three.module.js';\nimport { loadTayoBus } from './bus-loader.js';")
app=app.replace("$('#test').addEventListener('click',runAutoTest);",'')
app=app.replace("$('#restart').addEventListener('click',restartGame);",'')
app=app.replace("$('#viewAbove').addEventListener('click',()=>setView('top'));",'')
app=app.replace("if(e.key.toLowerCase()==='r')restartGame()", "if(e.key.toLowerCase()==='r'){if(driveMode==='drive')resetDrive();else restartGame()}if(e.key.toLowerCase()==='c'&&driveMode==='drive')driveCamera=driveCamera==='chase'?'front':'chase'")
app=app.replace("function attack(){if(!game.active", "function attack(){if(driveMode==='drive')return;if(!game.active")
app=app.replace("if(s)s.textContent=message;", "if(s)s.textContent=message;status.textContent=message;")
app=app.replace("const nextHeading=driveHeading+driveSpeed/driveWheelbase*Math.tan(driveSteer)*dt,forwardX=Math.sin((driveHeading+nextHeading)/2),forwardZ=Math.cos((driveHeading+nextHeading)/2),nx=bus.position.x+forwardX*driveSpeed*dt,nz=bus.position.z+forwardZ*driveSpeed*dt,q=driveProject(nx,nz),fit=driveFootprintCheck(nx,nz,nextHeading);", "const probeHeading=driveHeading+driveSpeed/driveWheelbase*Math.tan(driveSteer)*dt,probeX=bus.position.x+Math.sin((driveHeading+probeHeading)/2)*driveSpeed*dt,probeZ=bus.position.z+Math.cos((driveHeading+probeHeading)/2)*driveSpeed*dt,probe=driveProject(probeX,probeZ);if(driveCoursePhase==='return'&&driveSpeed<0&&probe.station<5)driveSpeed=Math.max(driveSpeed,-Math.sqrt(8*Math.max(0,probe.station-2.8)));const nextHeading=driveHeading+driveSpeed/driveWheelbase*Math.tan(driveSteer)*dt,forwardX=Math.sin((driveHeading+nextHeading)/2),forwardZ=Math.cos((driveHeading+nextHeading)/2),nx=bus.position.x+forwardX*driveSpeed*dt,nz=bus.position.z+forwardZ*driveSpeed*dt,q=driveProject(nx,nz),fit=driveFootprintCheck(nx,nz,nextHeading);")
app=app.replace('driveLineGroup.add(edge)', 'driveDebugGroup.add(edge)')
app=app.replace('function makeDriveDebug(){driveDebugGroup.clear();', 'function makeDriveDebug(){')
app=app.replace("driveDebugGroup.visible=e.target.checked", "driveDebugGroup.visible=e.target.checked;if(driveWire)driveWire.visible=e.target.checked")
app=app.replace("const names={top:'phase3a_top.png',bridge:'phase3a_top.png',side:'phase3a_top.png',robot:'phase3a_game.png'};", "const names={top:'d1_overview.png',bridge:'d1_overview.png',side:'d1_overview.png',robot:driveMode==='drive'?(driveCamera==='chase'?'d1_drive_start.png':'d1_drive_turn.png'):'d1_battle_mode.png',bus:driveCamera==='chase'?'d1_drive_start.png':'d1_drive_turn.png'};")
app=app.replace("driveCamera==='chase'?'d1_drive_start.png':'d1_drive_turn.png'", "driveCamera==='chase'?'d1_drive_start.png':driveCamera==='above'?'d1_overview.png':'d1_drive_turn.png'")
app=app.replace("camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25", "camera.lookAt(look)}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25")
app=app.replace("camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25,bus.position.y+2.0,bus.position.z+Math.cos(h)*.2),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*10,bus.position.y+1.6,bus.position.z+Math.cos(h)*10))", "camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))")
app=app.replace("}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode", "}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode")
app=app.replace("driveCamera=driveCamera==='chase'?'front':'chase'", "driveCamera=driveCamera==='chase'?'above':'chase'")
app=app.replace("$('#vehicleHud').style.display=driving?'grid':'none';", "$('#vehicleHud').style.display=driving?'grid':'none';$('#controlsHint').textContent=driving?'W アクセル · S ブレーキ/後退 · A/D ハンドル · C カメラ · R コース再開':'WASD 移動 · Space / J 攻撃 · HP表示 · R 再開';")
app=app.replace("$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?setDriveMode('battle'):setView('top')});", "$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?driveCamera='above':setView('top')});")
app=app.replace('/__phase3a_screenshot__/', '/__phaseD1_screenshot__/')
app=app.replace("const root=new THREE.Group(),navGroup", "const driveGroup=new THREE.Group();scene.add(driveGroup);const root=new THREE.Group(),navGroup")
app=app.replace("function render(data,nav,veg){", (ROOT/'scripts/phaseD1/drive-runtime.js').read_text(encoding='utf-8')+"\nfunction render(data,nav,veg){")
app=app.replace("$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?setDriveMode('battle'):setView('top')});", "$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?driveCamera='above':setView('top')});")
app=app.replace("camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25", "camera.lookAt(look)}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25")
app=app.replace("if(s)s.textContent=message;", "if(s)s.textContent=message;status.textContent=message;")
app=app.replace("setView('robot');restartGame();$('#vegetationStat')", "setView('robot');restartGame();initDrive().catch(e=>{const q=$('#driveStatus');if(q)q.textContent='バス読込エラー · '+e.message});$('#vegetationStat')")
app=app.replace("if(viewMode==='robot'&&robotPos){", "if(driveMode==='drive'&&bus){const h=driveHeading,look=new THREE.Vector3(bus.position.x, bus.position.y+1.15,bus.position.z);if(driveCamera==='chase'){const px=bus.position.x-Math.sin(h)*8.4,pz=bus.position.z-Math.cos(h)*8.4;camera.position.lerp(new THREE.Vector3(px,bus.position.y+4.1,pz),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25,bus.position.y+2.0,bus.position.z+Math.cos(h)*.2),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*10,bus.position.y+1.6,bus.position.z+Math.cos(h)*10))}}else if(viewMode==='robot'&&robotPos){")
app=app.replace("camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode", "camera.lookAt(look)}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode")
app=app.replace("$('#cameraToggle').addEventListener('click',()=>{driveCamera=driveCamera==='chase'?'front':'chase'});", "$('#cameraToggle').addEventListener('click',()=>{driveCamera=driveCamera==='chase'?'above':'chase'});")
app=app.replace("$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?setDriveMode('battle'):setView('top')});", "$('#viewAbove').addEventListener('click',()=>{driveMode==='drive'?driveCamera='above':setView('top')});")
app=app.replace("if(driveCamera==='chase'){const px=bus.position.x-Math.sin(h)*8.4,pz=bus.position.z-Math.cos(h)*8.4;camera.position.lerp(new THREE.Vector3(px,bus.position.y+4.1,pz),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}", "if(driveCamera==='chase'){const px=bus.position.x-Math.sin(h)*8.4,pz=bus.position.z-Math.cos(h)*8.4;camera.position.lerp(new THREE.Vector3(px,bus.position.y+4.1,pz),.12);camera.lookAt(look)}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}")
app=app.replace("camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25,bus.position.y+2.0,bus.position.z+Math.cos(h)*.2),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*10,bus.position.y+1.6,bus.position.z+Math.cos(h)*10))", "camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))")
app=app.replace("camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25", "camera.lookAt(look)}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*.25")
app=app.replace("if(loaded&&robotPos){const x=", "if(loaded&&robotPos&&driveMode==='battle'){const x=")
app=app.replace("combat(dt);if(now-lastLod", "combat(dt);updateDrive(dt);if(now-lastLod")
app=app.replace("gameGroup.traverse(o=>{if(o.isMesh)meshes++});", "gameGroup.traverse(o=>{if(o.isMesh)meshes++});driveGroup.traverse(o=>{if(o.isMesh)meshes++});")
app=app.replace("'敵HP '+game.enemyHp}`", "driveMode==='drive'?'BUS '+driveSpeed.toFixed(1)+' m/s':('敵HP '+game.enemyHp)}`")
app=app.replace("}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode", "}else if(driveCamera==='above'){camera.position.lerp(new THREE.Vector3(bus.position.x+22,bus.position.y+36,bus.position.z+24),.12);camera.lookAt(look)}else{camera.position.lerp(new THREE.Vector3(bus.position.x+Math.sin(h)*2.0,bus.position.y+2.0,bus.position.z+Math.cos(h)*2.0),.24);camera.lookAt(new THREE.Vector3(bus.position.x+Math.sin(h)*12,bus.position.y+1.5,bus.position.z+Math.cos(h)*12))}}else if(viewMode")
(web/'app.js').write_text(app,encoding='utf-8')
print('Built',web)
print('Course A',round(length,2),'m; way',route['wayId'],'; modeled width',width,'m; bus envelope',round(bus_width,2),'x',round(bus_length,2),'m; min path radius',round(min_radius,2) if min_radius else None,'m')
print('B/C candidates are report-only and remain blocked from driving.')
