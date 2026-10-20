from pathlib import Path
import json, math, shutil, runpy, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'build-phase2i'; BUILD=ROOT/'build-phase2j'
if not SOURCE.exists(): raise SystemExit('Missing preserved build-phase2i viewer/data.')
if BUILD.exists(): shutil.rmtree(BUILD)
shutil.copytree(SOURCE,BUILD)
WEB=BUILD/'web/phase2i'; WEB.rename(BUILD/'web/phase2j'); WEB=BUILD/'web/phase2j'
P2F=json.loads((ROOT/'data/processed/phase2f/bridge_deck_candidate.json').read_text(encoding='utf-8'))
ALIGN=json.loads((ROOT/'data/processed/phase2e/phase2e_bridge_alignment.json').read_text(encoding='utf-8'))
project=runpy.run_path(str(ROOT/'scripts/phase1/build_phase1_data.py'))['proj']
raw=[ROOT/'data/raw/osm/layers/paths/footpaths.osm',ROOT/'data/raw/osm/layers/paths/bridges.osm']
nodes={}; ways={}
for f in raw:
    for e in ET.parse(f).getroot():
        if e.tag=='node': nodes[e.get('id')]=(float(e.get('lat')),float(e.get('lon')))
        elif e.tag=='way': ways[e.get('id')]=([n.get('ref') for n in e.findall('nd')],{t.get('k'):t.get('v') for t in e.findall('tag')})

def local(lat,lon):
    # Same EPSG:6677 projection helper used by Phase 1 and 2F, read only.
    x,n=project(lat,lon)
    return {'x':x,'z':-n}
def length(refs):
    p=[local(*nodes[r]) for r in refs]
    return sum(math.hypot(b['x']-a['x'],b['z']-a['z']) for a,b in zip(p,p[1:]))
def way(wid):
    refs,tags=ways[wid]
    return {'wayId':wid,'nodeRefs':refs,'points':[{'nodeId':r,'lat':nodes[r][0],'lon':nodes[r][1],**local(*nodes[r])} for r in refs], 'lengthProjectedMetres':length(refs),'tags':tags,'source':'raw OSM extract; read-only'}
trunk=way('33976871'); arm1=way('598428792'); arm2=way('683394375'); outline=way('745579214')
assert trunk['nodeRefs'][0]==arm1['nodeRefs'][-1]==arm2['nodeRefs'][0]=='6980957124'
assert outline['nodeRefs'][0]==outline['nodeRefs'][-1]
op=[nodes[r] for r in outline['nodeRefs']]
lat0,lat1=min(p[0] for p in op),max(p[0] for p in op); lon0,lon1=min(p[1] for p in op),max(p[1] for p in op)
ox=[p['x'] for p in outline['points']]; oz=[p['z'] for p in outline['points']]
outline.update({'closed':True,'nodeCount':len(outline['nodeRefs']),'bboxLatLon':[lat0,lon0,lat1,lon1],
 'northSouthExtentProjectedMetres':max(oz)-min(oz),'eastWestExtentProjectedMetres':max(ox)-min(ox)})
route1=trunk['lengthProjectedMetres']+arm1['lengthProjectedMetres']; route2=trunk['lengthProjectedMetres']+arm2['lengthProjectedMetres']
display=149.445; clipped=132.836; gap=16.609
axis=(82.1,-132.1); station=0.; nearest=(math.inf,0.)
for a,b in zip(trunk['points'],trunk['points'][1:]):
    dx=b['x']-a['x']; dz=b['z']-a['z']; seg=math.hypot(dx,dz)
    t=max(0.,min(1.,((axis[0]-a['x'])*dx+(axis[1]-a['z'])*dz)/(seg*seg)))
    d=math.hypot(axis[0]-a['x']-t*dx,axis[1]-a['z']-t*dz)
    if d<nearest[0]: nearest=(d,station+t*seg)
    station+=seg
analysis={
 'phase':'2J','coordinateReference':'OSM source geometry is WGS84 lat/lon; analysis and Three.js plan traces use the same EPSG:6677 projection helper as Phase 1/2F. Plan display only, no elevation/collision.',
 'sourceFiles':[str(f.relative_to(ROOT)) for f in raw],
 'publicReferences':[
  {'value':250,'unit':'m','topic':'Kiba Park Ohashi total length','class':'park-management-and-JCI-archive','source':'Tokyo Metropolitan Park Management Plan and Japan Concrete Institute archive; overall bridge linking three zones.','url':'https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/070328kbetsumpkiba'},
  {'value':96.95,'unit':'m','topic':'maximum span','class':'JCI-engineering-archive','source':'Japan Concrete Institute archive: 2-span continuous PC cable-stayed bridge.','url':'https://www.jci-net.or.jp/photo_60/archive/detail_db.php?id=168&page=6'},
  {'value':60,'unit':'m','topic':'pylon height','class':'Tokyo-park-management-plan','source':'Tokyo Metropolitan Park Management Plan.','url':'https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/070328kbetsumpkiba'},
  {'value':186,'unit':'m','topic':'bridge length','class':'PC-construction-engineering-publication','source':'Prestressed Concrete Construction Association, 1995 seminar text: Kiba Park Bridge; 2-span continuous PC cable-stayed, maximum span 97.0m, standard width 10.8–25.8m, split portion 8.228m.','url':'https://jpci.or.jp/data/pc-seminar/text/023_pc-seminar-text_199502.pdf'},
  {'value':97,'unit':'m','topic':'maximum span (rounded)','class':'PC-construction-engineering-publication','source':'Same 1995 technical text; rounds consistently with JCI 96.95m.','url':'https://jpci.or.jp/data/pc-seminar/text/023_pc-seminar-text_199502.pdf'}],
 'definitionConflict':{'250m':'Park plan/JCI say 250m but do not state measurement endpoints or whether approach walkways are included.','186m':'1995 technical reference calls the engineered 2-span bridge length 186m. Sources reviewed do not reconcile scope.','differenceMetres':64,'interpretation':'Possible structure-versus-whole-route scope difference; inference only, not a confirmed accounting.'},
 'osm':{'license':'© OpenStreetMap contributors, ODbL 1.0','trunk':trunk,'southBranches':[arm1,arm2],'sharedJunctionNode':'6980957124',
  'northToSouthRouteLengthsMetres':{'north_terminal_to_6400941151_via_598428792':route1,'north_terminal_to_6400941152_via_683394375':route2},
  'threeArmUnionEdgeLengthMetres':trunk['lengthProjectedMetres']+arm1['lengthProjectedMetres']+arm2['lengthProjectedMetres'],'bridgeFootprint':outline},
 'phase2f':{'displayedWay33976871PlusGapMetres':display,'clippedCenterlineInParkMetres':clipped,'boundaryGapVisualFillMetres':gap,
  'rawWay33976871Metres':trunk['lengthProjectedMetres'],'wayLengthOutsideDisplayedCandidateMetres':trunk['lengthProjectedMetres']-display,
  '250mArithmeticResidualMetres':250-display,'186mArithmeticResidualMetres':186-display,'gapCause':'park polygon clipping; separately identified in Phase 2I'},
 'g62':{'boundsXYZMetres':ALIGN['asset']['boundsXYZ'],'xyzDimensionsMetres':ALIGN['asset']['dimensionsXYZMetres'],
  'approxPylonAxisLocalXZ':{'west':[76.0,-132.1],'east':[88.2,-132.1],'midpoint':[82.1,-132.1]},'pylonHeightMetres':60,'deckMeshPresent':False,
  'registration':'Identity visual hypothesis only; no survey control; GLB axis metadata contradicts vertex convention.'},
 'alignmentAudit':{'phase2gLateralNearestDistanceToOSM33976871Metres':nearest[0],'basis':'Recomputed in the Phase 1/2F EPSG:6677 local frame from raw OSM way geometry and G6.2 tower-axis midpoint; agrees with Phase 2G report to rounding.',
  'towerApproxStationFromSharedJunctionMetres':nearest[1],'approxRemainingToNorthEndMetres':trunk['lengthProjectedMetres']-nearest[1],
  'spanCheck':'These approximate asymmetric station distances do not validate a 96.95/97m maximum span. G6.2 lacks deck endpoints and registration survey.'},
 'derivedComparisonsMetres':{'way33976871':trunk['lengthProjectedMetres'],'phase2fDisplayed':display,'rawWayMinusPhase2f':trunk['lengthProjectedMetres']-display,
  '250MinusPhase2f':250-display,'186MinusPhase2f':186-display,'250Minus186':64,'northToSouthViaArm598':route1,'northToSouthViaArm683':route2},
 'conclusion':'250m−149.445mは算術上の差であり、位置が特定された単一欠落区間ではない。OSMには174.289mの主線と76.8–78.0mの二つの枝が共有節点でつながる三分岐歩道がある。北端から南側の各枝端までの経路は約251.1mと252.3mで、公表250m値に近い。これは全体ルート解釈を支持するが証明しない。186mの技術資料値との範囲定義は未解決。追加橋梁メッシュを制作する根拠はない。',
 'navigationPreserved':True,'bridgeRunStates':{'review':8,'blocked':5,'walkable':0},'productionNavigationModified':False}
out=BUILD/'data/processed/phase2j'; out.mkdir(parents=True,exist_ok=True)
(out/'bridge_scope_analysis.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2),encoding='utf-8')

html=(WEB/'index.html').read_text(encoding='utf-8')
html=html.replace('木場公園 Phase 2I · Vegetation','木場公園 Phase 2J · Bridge scope').replace('木場公園 · Phase 2I 橋梁移動実験','木場公園 · Phase 2J 橋梁範囲調査').replace('Phase 2I PNG保存','Phase 2J PNG保存')
html=html.replace('</section><section id="legend">','<fieldset id="scopeEvidence"><legend>Phase 2J · OSM橋梁範囲（平面位置のみ）</legend><label><input id="osmTrace" type="checkbox" checked> OSM線形・橋梁外形を表示（標高／床版ではない）</label><small>way 33976871 主線 174.289m · way 598428792 / 683394375 分岐 78.0m / 76.8m</small><small>閉じたOSM橋梁外形 745579214 · 公開値250m / 技術資料186mは定義未照合</small><small>線は表示用に上方オフセット。未再現量を特定位置へ延長していません。</small></fieldset></section><section id="legend">')
html=html.replace('<span>下面・欄干：寸法推定／衝突なし</span>','<span>OSM平面トレース：高さなし</span><span>下面・欄干：寸法推定／衝突なし</span>')
(WEB/'index.html').write_text(html,encoding='utf-8')
css=(WEB/'style.css').read_text(encoding='utf-8')+'\n#scopeEvidence{border:1px solid #8b9b90;border-radius:8px;padding:7px;margin:5px 2px}#scopeEvidence small{display:block;line-height:1.35;margin:3px 0}\n'
(WEB/'style.css').write_text(css,encoding='utf-8')
js=(WEB/'app.js').read_text(encoding='utf-8')
js=js.replace('gapGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup,bridgeGroup,deckGroup,trialGroup,gapGroup);','gapGroup=new THREE.Group(),evidenceGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup,bridgeGroup,deckGroup,trialGroup,gapGroup,evidenceGroup);')
fn="""function drawPhase2jEvidence(d){function line(points,color,dash,gap,closed=false){const g=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(p.x,8.5,p.z)));const m=new THREE.LineDashedMaterial({color,dashSize:dash,gapSize:gap,transparent:true,opacity:.96,depthTest:false});const o=closed?new THREE.LineLoop(g,m):new THREE.Line(g,m);o.computeLineDistances();o.userData={osmPlanOnly:true,elevationKnown:false,collisionEnabled:false};evidenceGroup.add(o)}line(d.osm.trunk.points,0x00c8ff,5,2);line(d.osm.southBranches[0].points,0xffc247,4,2);line(d.osm.southBranches[1].points,0xe064ff,4,2);line(d.osm.bridgeFootprint.points,0xf2f4cf,3,2,true);evidenceGroup.visible=true;document.querySelector('#osmTrace').addEventListener('change',e=>evidenceGroup.visible=e.target.checked)}
"""
js=js.replace('function drawPhase2iGap(data){',fn+'function drawPhase2iGap(data){')
needle="fetch('../../data/processed/phase2d/phase2d_vegetation.json').then(r=>{if(!r.ok)throw Error(`Phase 2D HTTP ${r.status}`);return r.json()})])"
rep="fetch('../../data/processed/phase2d/phase2d_vegetation.json').then(r=>{if(!r.ok)throw Error(`Phase 2D HTTP ${r.status}`);return r.json()}),fetch('../../data/processed/phase2j/bridge_scope_analysis.json').then(r=>{if(!r.ok)throw Error(`Phase 2J HTTP ${r.status}`);return r.json()})])"
if needle not in js: raise SystemExit('Cannot locate Phase 2D fetch list in copied viewer')
js=js.replace(needle,rep).replace('([gapCandidate,trial,deck,a,b,c])=>{gapData=gapCandidate;','([gapCandidate,trial,deck,a,b,c,evidence])=>{gapData=gapCandidate;').replace('render(a,b,c);drawTrialMeshes(trial);','render(a,b,c);drawPhase2jEvidence(evidence);drawTrialMeshes(trial);')
js=js.replace('/__phase2i_screenshot__/','/__phase2j_screenshot__/').replace('phase2i_top.png','phase2j_top.png').replace('phase2i_bridge.png','phase2j_bridge.png').replace('phase2i_side.png','phase2j_side.png').replace('phase2i_robot.png','phase2j_robot.png')
(WEB/'app.js').write_text(js,encoding='utf-8')
print('Phase 2J built:',WEB)
print('OSM way and branch lengths:',*(round(x,3) for x in (trunk['lengthProjectedMetres'],arm1['lengthProjectedMetres'],arm2['lengthProjectedMetres'],route1,route2)))
print('OSM footprint EPSG:6677 bounds (E-W x N-S):',round(outline['eastWestExtentProjectedMetres'],2),'x',round(outline['northSouthExtentProjectedMetres'],2),'m')
