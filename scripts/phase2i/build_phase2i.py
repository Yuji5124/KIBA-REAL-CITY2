from pathlib import Path
import json, math, shutil

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build-phase2i'
if BUILD.exists():
    shutil.rmtree(BUILD)
shutil.copytree(ROOT / 'build-phase2h', BUILD)
WEB = BUILD / 'web' / 'phase2i'
shutil.copytree(BUILD / 'web' / 'phase2h', WEB)
TRIAL = json.loads((BUILD / 'data/processed/phase2h/bridge_trial_surface.json').read_text(encoding='utf-8'))
VISUAL = json.loads((BUILD / 'data/processed/phase2f/bridge_deck_candidate.json').read_text(encoding='utf-8'))
RUN_A, RUN_B = TRIAL['runs']
A, B = RUN_A['points'][-1], RUN_B['points'][0]
PA, PB = RUN_A['points'][-2], RUN_B['points'][1]

def unit(p, q):
    d = math.hypot(q['x']-p['x'], q['z']-p['z'])
    return ((q['x']-p['x'])/d, (q['z']-p['z'])/d)

u, v = unit(PA, A), unit(B, PB)
handle = 3.0
C1 = (A['x'] + u[0]*handle, A['z'] + u[1]*handle)
C2 = (B['x'] - v[0]*handle, B['z'] - v[1]*handle)
chord = math.hypot(B['x']-A['x'], B['z']-A['z'])
theta = math.atan2(B['z']-A['z'], B['x']-A['x'])
hA = math.degrees(math.atan2(u[1], u[0]))
hB = math.degrees(math.atan2(v[1], v[0]))
turn = (hB-hA+180) % 360 - 180

def bezier(t):
    s = 1-t
    x = s**3*A['x'] + 3*s*s*t*C1[0] + 3*s*t*t*C2[0] + t**3*B['x']
    z = s**3*A['z'] + 3*s*s*t*C1[1] + 3*s*t*t*C2[1] + t**3*B['z']
    smooth = 3*t*t - 2*t*t*t
    y = A['y'] + (B['y']-A['y'])*smooth
    return {'x':x,'y':y,'z':z,'t':t}

curve_n = 180
curve = [bezier(i/curve_n) for i in range(curve_n+1)]
curve_len = sum(math.dist([curve[i-1][k] for k in ('x','y','z')],[curve[i][k] for k in ('x','y','z')]) for i in range(1,len(curve)))
max_chord_deviation = max(math.hypot(p['x']-(A['x']+(B['x']-A['x'])*p['t']),p['z']-(A['z']+(B['z']-A['z'])*p['t'])) for p in curve)
max_grade_pct = 100*abs(B['y']-A['y'])*1.5/chord

def point_at(run, station):
    pts = run['points']; i = 1
    while i < len(pts)-1 and pts[i]['station'] < station: i += 1
    p, q = pts[i-1], pts[i]
    f = (station-p['station'])/(q['station']-p['station']) if q['station'] != p['station'] else 0
    return {'x':p['x']+(q['x']-p['x'])*f,'y':p['y']+(q['y']-p['y'])*f,'z':p['z']+(q['z']-p['z'])*f}

margin = 0.75
approach_a_len = RUN_A['lengthMetres']-margin
approach_b_len = margin
approach_a_steps = max(1, math.ceil(margin/.08))
approach_b_steps = max(1, math.ceil(margin/.08))
path = [point_at(RUN_A, approach_a_len + margin*i/approach_a_steps) for i in range(approach_a_steps+1)]
path.extend([{k:p[k] for k in ('x','y','z')} for p in curve[1:]])
path.extend([point_at(RUN_B, margin*i/approach_b_steps) for i in range(1,approach_b_steps+1)])
for i,p in enumerate(path): p['index'] = i

surfaces = []
for i in range(len(curve)-1):
    p,q = curve[i],curve[i+1]
    dx,dz = q['x']-p['x'],q['z']-p['z']; length = math.hypot(dx,dz)
    nx,nz = -dz/length,dx/length; half=2.0; render=.025
    surfaces.append([[p['x']+nx*half,p['y']+render,p['z']+nz*half],[p['x']-nx*half,p['y']+render,p['z']-nz*half],[q['x']+nx*half,q['y']+render,q['z']+nz*half],[q['x']-nx*half,q['y']+render,q['z']-nz*half]])

visual_gap = VISUAL['gap']
gap_data = {
 'phase':'2I','coordinateSystem':TRIAL['coordinateSystem'],'sourcePhase2H':'bridge_trial_surface.json','sourcePhase2F':'bridge_deck_candidate.json','sourceOSMWayId':'33976871',
 'cause':{'classification':'park_boundary_clipping','rawOSMWayContinuous':True,'rawOSMWayNodeCount':3,'rawOSMWayLengthMetres':174.289,'clipAlgorithm':'Phase 2A clipped_runs splits OSM segments at the park polygon and retains only inside intervals; Phase 2C preserves two runs without auto-joining them.','terrainInterpolationCausedHorizontalGap':False,'visualCandidateSource':'Phase 2F added a collision-disabled straight visual span after the clip; its height is linearly interpolated from estimated Phase 2C endpoints.'},
 'gap':{'horizontalMetres':chord,'threeDimensionalEndpointDistanceMetres':math.dist([A['x'],A['y'],A['z']],[B['x'],B['y'],B['z']]),'heightDeltaMetres':B['y']-A['y'],'straightGradePercent':100*(B['y']-A['y'])/chord,'bearingDegreesFromPositiveX':math.degrees(theta),'gapAEnd':A,'gapBStart':B,'runATerminalTangentDegrees':hA,'runBInitialTangentDegrees':hB,'tangentTurnDegrees':turn,'runATerminalGradePercent':100*(A['y']-PA['y'])/math.hypot(A['x']-PA['x'],A['z']-PA['z']),'runBInitialGradePercent':100*(PB['y']-B['y'])/math.hypot(PB['x']-B['x'],PB['z']-B['z'])},
 'phase2FVisualGap':{'lengthMetres':visual_gap['lengthMetres'],'heightDeltaMetres':visual_gap['heightDeltaMetres'],'candidateWidthMetres':visual_gap['candidateWidthMetres'],'collisionEnabled':visual_gap['collisionEnabled'],'maxCenterlineOffsetMetres':max_chord_deviation,'straightHalfWidthMetres':2.0},
 'connectionCandidate':{'enabledByDefault':False,'requiresPhase2HTrialMode':True,'widthMetres':4.0,'widthIsEstimated':True,'heightMethod':'cubic Bezier XY tangent match; smoothstep interpolation between Phase 2H estimated run endpoint elevations; no surveyed deck heights','heightIsEstimated':True,'bezierHandleMetres':handle,'centerlineLengthMetres':curve_len,'pointCount':len(curve),'centerline':[{k:p[k] for k in ('x','y','z')} for p in curve],'compositeTrialPath':path,'surfaceQuads':surfaces,'renderOffsetMetres':.025,'renderOffsetIsPhysicalHeight':False,'maximumEstimatedGradePercent':max_grade_pct,'collisionHalfWidthAfterRobotRadiusMetres':1.72,'doesNotConnectToUnmodeledExtent':True,'approachMarginsMetres':[margin,margin],'unmodeledProbe':{'x':RUN_B['points'][-1]['x']+(RUN_B['points'][-1]['x']-RUN_B['points'][-2]['x'])/math.hypot(RUN_B['points'][-1]['x']-RUN_B['points'][-2]['x'],RUN_B['points'][-1]['z']-RUN_B['points'][-2]['z'])*100.555,'z':RUN_B['points'][-1]['z']+(RUN_B['points'][-1]['z']-RUN_B['points'][-2]['z'])/math.hypot(RUN_B['points'][-1]['x']-RUN_B['points'][-2]['x'],RUN_B['points'][-1]['z']-RUN_B['points'][-2]['z'])*100.555}},
 'unmodeledOverallLengthMetres':100.555,'productionNavigationModified':False,'autoConnectionInNormalMode':False,
 'limitations':['This is a DEV-only geometric experiment, not a measured bridge surface.','The curve interpolates an OSM boundary clip gap; it does not establish physical deck continuity.','The hypothetical 100.555m probe checks absence of connection geometry, not the actual location of the unmodeled bridge extent.','No terrain/structural support data validates the connection candidate.']}
out = BUILD/'data/processed/phase2i'; out.mkdir(parents=True,exist_ok=True)
(out/'bridge_gap_connection.json').write_text(json.dumps(gap_data,ensure_ascii=False,indent=2),encoding='utf-8')

app_path = WEB/'app.js'; app = app_path.read_text(encoding='utf-8')
app=app.replace("deckGroup=new THREE.Group(),trialGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup,bridgeGroup,deckGroup,trialGroup);","deckGroup=new THREE.Group(),trialGroup=new THREE.Group(),gapGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup,bridgeGroup,deckGroup,trialGroup,gapGroup);",1)
app=app.replace("let trialData=null,trialMode=false,trialRunIndex=0,trialStation=0,trialState='disabled',normalRobotPosBeforeTrial=null,navData,phaseData,robot,robotPos=null,","let gapData=null,gapCandidateOn=false,trialData=null,trialMode=false,trialRunIndex=0,trialStation=0,trialState='disabled',normalRobotPosBeforeTrial=null,navData,phaseData,robot,robotPos=null,",1)
app=app.replace("Promise.all([fetch('../../data/processed/phase2h/bridge_trial_surface.json')","Promise.all([fetch('../../data/processed/phase2i/bridge_gap_connection.json').then(r=>{if(!r.ok)throw Error('Phase 2I HTTP '+r.status);return r.json()}),fetch('../../data/processed/phase2h/bridge_trial_surface.json')",1)
app=app.replace(".then(async ([trial,deck,a,b,c])=>{trialData=trial;render(a,b,c);drawTrialMeshes(trial);",".then(async ([gapCandidate,trial,deck,a,b,c])=>{gapData=gapCandidate;trialData=trial;render(a,b,c);drawTrialMeshes(trial);drawPhase2iGap(gapCandidate);",1)
app=app.replace("if(trialGroup.visible)trialGroup.traverse(o=>{if(o.isMesh)meshes++});perf.textContent=","if(trialGroup.visible)trialGroup.traverse(o=>{if(o.isMesh)meshes++});if(gapGroup.visible)gapGroup.traverse(o=>{if(o.isMesh)meshes++});perf.textContent=",1)
app=app.replace("$('#trialMode').addEventListener('change',e=>setTrialMode(e.target.checked));","$('#trialMode').addEventListener('change',e=>{setTrialMode(e.target.checked);if(!e.target.checked)setGapCandidate(false)});",1)
before = 'const keys=new Set();'
runtime = r'''
function drawPhase2iGap(data){const p=[],ix=[];for(const q of data.connectionCandidate.surfaceQuads){const n=p.length/3;for(const v of q)p.push(...v);ix.push(n,n+2,n+1,n+1,n+2,n+3)}const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setIndex(ix);g.computeVertexNormals();const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:0x20d6d0,roughness:.9,side:THREE.DoubleSide,depthWrite:true}));m.name='Phase 2I DEV-only estimated gap connection';m.userData={devOnly:true,estimated:true,productionNavigation:false};gapGroup.add(m);gapGroup.visible=false}
function gapSupport(x,z){const pts=gapData.connectionCandidate.compositeTrialPath;let best={d:Infinity,s:0,y:0,atEndpoint:false},station=0;for(let i=1;i<pts.length;i++){const a=pts[i-1],b=pts[i],dx=b.x-a.x,dz=b.z-a.z,l2=dx*dx+dz*dz,t=l2?((x-a.x)*dx+(z-a.z)*dz)/l2:0;if((i===1&&t<0)||(i===pts.length-1&&t>1))return {ok:false,reason:'bounded_connection_endpoint'};const f=Math.max(0,Math.min(1,t)),px=a.x+f*dx,pz=a.z+f*dz,d=Math.hypot(x-px,z-pz),seg=Math.hypot(dx,dz);if(d<best.d)best={d,s:station+f*seg,y:a.y+f*(b.y-a.y),atEndpoint:i===1||i===pts.length-1};station+=seg}if(best.d>gapData.connectionCandidate.collisionHalfWidthAfterRobotRadiusMetres)return {ok:false,reason:'outside_estimated_bridge_width'};return {ok:true,y:best.y,station:best.s,distance:best.d}}
function setGapCandidate(enabled){if(enabled&&!trialMode){document.querySelector('#gapCandidateToggle').checked=false;document.querySelector('#gapResult').textContent='BLOCK · DEV接続候補には実験モードが必要';return}gapCandidateOn=enabled;gapGroup.visible=enabled&&trialMode;document.querySelector('#gapResult').textContent=enabled?'DEV接続候補 ON · 推定のみ · 通常ナビ不変':'DEV接続候補 OFF · 16.609mギャップ BLOCK';}
function runGapTraversal(direction){if(!trialMode){document.querySelector('#gapResult').textContent='BLOCK · 先に実験モードを有効化';return}if(!gapCandidateOn){document.querySelector('#gapResult').textContent='BLOCK · DEV接続候補 OFF · 16.609mギャップ';return}const pts=gapData.connectionCandidate.compositeTrialPath,ordered=direction>0?pts:[...pts].reverse(),start=ordered[0],end=ordered[ordered.length-1];robotPos={x:start.x,y:start.y,z:start.z};robot.position.set(robotPos.x,robotPos.y,robotPos.z);let ok=0,blocked=0,maxGrade=0;for(let i=1;i<ordered.length;i++){const a=ordered[i-1],b=ordered[i],q=gapSupport(b.x,b.z),horizontal=Math.hypot(b.x-a.x,b.z-a.z),vertical=Math.abs(b.y-a.y);if(horizontal>1e-8)maxGrade=Math.max(maxGrade,100*vertical/horizontal);if(!q.ok){blocked++;break}robotPos={x:b.x,y:q.y,z:b.z};robot.position.set(robotPos.x,robotPos.y,robotPos.z);robot.rotation.y=Math.atan2(b.x-a.x,b.z-a.z);ok++}const curve=gapData.connectionCandidate.centerline,mi=Math.floor(curve.length/2),mid=curve[mi],dx=curve[mi+1].x-curve[mi-1].x,dz=curve[mi+1].z-curve[mi-1].z,n=Math.hypot(dx,dz)||1,side=gapSupport(mid.x+(-dz/n)*1.82,mid.z+(dx/n)*1.82),far=gapData.connectionCandidate.unmodeledProbe,unmodeled=gapSupport(far.x,far.z),prevEnd=ordered[ordered.length-2],endLen=Math.hypot(end.x-prevEnd.x,end.z-prevEnd.z),endProbe=gapSupport(end.x+(end.x-prevEnd.x)/endLen*.1,end.z+(end.z-prevEnd.z)/endLen*.1);const lateralBlocked=!side.ok,unmodeledBlocked=!unmodeled.ok,endpointBlocked=!endProbe.ok;trialRunIndex=direction>0?1:0;trialStation=direction>0?.75:trialData.runs[0].lengthMetres-.75;document.querySelector('#gapResult').textContent=(direction>0?'A → B':'B → A')+' '+(blocked===0?'PASS':'BLOCK')+' · '+ok+' steps · max grade '+maxGrade.toFixed(2)+'% · 横逸脱 '+(lateralBlocked?'BLOCK':'FAIL')+' · 終端 '+(endpointBlocked?'BLOCK':'FAIL')+' · 未モデル化 '+(unmodeledBlocked?'BLOCK':'FAIL');status.textContent='DEV限定接続試験 · Phase 2Cナビゲーションは未変更'}
'''
app=app.replace(before,runtime+'\n'+before,1)
handlers="$('#gapCandidateToggle').addEventListener('change',e=>setGapCandidate(e.target.checked));$('#gapForward').addEventListener('click',()=>runGapTraversal(1));$('#gapReverse').addEventListener('click',()=>runGapTraversal(-1));"
app=app.replace(before,handlers+before,1)
app=app.replace("phase2h_top.png","phase2i_top.png").replace("phase2h_bridge.png","phase2i_bridge.png").replace("phase2h_side.png","phase2i_side.png").replace("phase2h_robot.png","phase2i_robot.png").replace("/__phase2h_screenshot__/","/__phase2i_screenshot__/").replace("Phase 2H","Phase 2I")
app_path.write_text(app,encoding='utf-8')

html_path=WEB/'index.html'; html=html_path.read_text(encoding='utf-8').replace('Phase 2H','Phase 2I')
html=html.replace('</fieldset></section><section id="legend">','</fieldset><fieldset id="gapControls"><legend>DEV専用 · Run A/B ギャップ接続候補</legend><label><input id="gapCandidateToggle" type="checkbox">推定接続面 ON</label><button id="gapForward">A → B 横断</button><button id="gapReverse">B → A 横断</button><output id="gapResult">DEV接続候補 OFF · 16.609mギャップ BLOCK</output></fieldset></section><section id="legend">')
html=html.replace('Phase 2H PNG保存','Phase 2I PNG保存')
html_path.write_text(html,encoding='utf-8')
css=WEB/'style.css'; css.write_text(css.read_text(encoding='utf-8')+'\n#gapControls{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;border:1px dashed #238f8e;border-radius:8px}#gapControls legend{font-weight:700;color:#126c6a}#gapControls output{grid-column:1/-1;color:#234c4a;font-size:12px}#hud{max-height:calc(100vh - 30px);overflow-y:auto}\n',encoding='utf-8')
print('Phase 2I built:',WEB,'gap horizontal/3d:',round(chord,3),round(gap_data['gap']['threeDimensionalEndpointDistanceMetres'],3),'curve:',round(curve_len,3),'grade:',round(max_grade_pct,3),'deviation:',round(max_chord_deviation,3))
