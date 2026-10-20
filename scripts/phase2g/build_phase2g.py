from pathlib import Path
import shutil, json
root=Path(__file__).resolve().parents[2]
build=root/'build-phase2g'; web=build/'web'/'phase2g'; data=build/'data'
if build.exists(): shutil.rmtree(build)
web.mkdir(parents=True); (build/'reports').mkdir()
shutil.copytree(root/'build-phase2f'/'web'/'phase2f',web,dirs_exist_ok=True)
shutil.copytree(root/'build-phase2f'/'data',data,dirs_exist_ok=True)
shutil.copy2(root/'data'/'processed'/'phase2f'/'bridge_deck_candidate.json',data/'processed'/'phase2f'/'bridge_deck_candidate.json')
shutil.copy2(root/'data'/'processed'/'phase2e'/'phase2e_bridge_alignment.json',data/'processed'/'phase2e'/'phase2e_bridge_alignment.json')
app_path=web/'app.js'; app=app_path.read_text(encoding='utf-8')
anchor="Promise.all([fetch('../../data/processed/phase2f/bridge_deck_candidate.json')"
fn=r"""
function addPhase2gDetails(surfaces){
 const under=[],ui=[],rp=[],ri=[],cp=[],ci=[];
 const quad=(p,ix,a,b,c,d)=>{const n=p.length/3;for(const v of [a,b,c,d])p.push(...v);ix.push(n,n+1,n+2,n+2,n+1,n+3)};
 const boxBeam=(p,ix,a,b,w,offset,height)=>{
  const dx=b[0]-a[0],dz=b[2]-a[2],len=Math.hypot(dx,dz)||1,nx=-dz/len*w/2,nz=dx/len*w/2;
  const lo0=a[1]+offset,lo1=b[1]+offset,hi0=lo0+height,hi1=lo1+height;
  const A=[a[0]+nx,lo0,a[2]+nz],B=[a[0]-nx,lo0,a[2]-nz],C=[b[0]+nx,lo1,b[2]+nz],D=[b[0]-nx,lo1,b[2]-nz],E=[A[0],hi0,A[2]],F=[B[0],hi0,B[2]],G=[C[0],hi1,C[2]],H=[D[0],hi1,D[2]];
  quad(p,ix,A,B,C,D);quad(p,ix,E,G,F,H);quad(p,ix,A,E,B,F);quad(p,ix,C,D,G,H);quad(p,ix,A,C,E,G);quad(p,ix,B,F,D,H)
 };
 const mapped=surfaces.filter(s=>s.kind==='mapped_osm_route');
 for(const s of mapped){
  const [l0,r0,l1,r1]=s.corners,drop=.32;
  const dl0=[l0[0],l0[1]-drop,l0[2]],dr0=[r0[0],r0[1]-drop,r0[2]],dl1=[l1[0],l1[1]-drop,l1[2]],dr1=[r1[0],r1[1]-drop,r1[2]];
  quad(under,ui,dl0,dr0,dl1,dr1);quad(under,ui,l0,l1,dl0,dl1);quad(under,ui,r0,dr0,r1,dr1);
  for(const [a,b] of [[l0,l1],[r0,r1]]){
   boxBeam(cp,ci,a,b,.18,0,.18);
   boxBeam(rp,ri,a,b,.10,.96,.09);
   const span=Math.hypot(b[0]-a[0],b[2]-a[2]),count=Math.max(1,Math.floor(span/2));
   for(let k=0;k<=count;k++){const t=k/count,p=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];quad(rp,ri,[p[0]-.05,p[1],p[2]-.05],[p[0]+.05,p[1],p[2]-.05],[p[0]-.05,p[1]+.96,p[2]-.05],[p[0]+.05,p[1]+.96,p[2]-.05]);quad(rp,ri,[p[0]+.05,p[1],p[2]-.05],[p[0]+.05,p[1],p[2]+.05],[p[0]+.05,p[1]+.96,p[2]-.05],[p[0]+.05,p[1]+.96,p[2]+.05]);quad(rp,ri,[p[0]+.05,p[1],p[2]+.05],[p[0]-.05,p[1],p[2]+.05],[p[0]+.05,p[1]+.96,p[2]+.05],[p[0]-.05,p[1]+.96,p[2]+.05]);quad(rp,ri,[p[0]-.05,p[1],p[2]+.05],[p[0]-.05,p[1],p[2]-.05],[p[0]-.05,p[1]+.96,p[2]+.05],[p[0]-.05,p[1]+.96,p[2]-.05])}
  }
 }
 const make=(p,ix,mat,name)=>{if(!ix.length)return;const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setIndex(ix);g.computeVertexNormals();const m=new THREE.Mesh(g,mat);m.name=name;m.userData={estimated:true,collisionEnabled:false,source:'Phase 2F mapped OSM way 33976871'};deckGroup.add(m)};
 make(under,ui,new THREE.MeshStandardMaterial({color:0x92999e,roughness:.9,side:THREE.DoubleSide}),'Phase 2G underside · 0.32m estimate · visual only');
 make(cp,ci,new THREE.MeshStandardMaterial({color:0xa6aaad,roughness:.82,side:THREE.DoubleSide}),'Phase 2G curbs · 0.18m estimate · visual only');
 make(rp,ri,new THREE.MeshStandardMaterial({color:0x626d70,roughness:.72,side:THREE.DoubleSide}),'Phase 2G guardrails · 1.05m estimate · visual only');
 return {mappedQuads:mapped.length,detailMeshes:deckGroup.children.length,collisionEnabled:false}
}
"""
if anchor not in app: raise RuntimeError('Missing Phase 2F candidate load anchor')
app=app.replace(anchor,fn+'\n'+anchor,1)
for a,b in [('phase2f_top.png','phase2g_top.png'),('phase2f_bridge.png','phase2g_bridge.png'),('phase2f_side.png','phase2g_side.png'),('phase2f_robot.png','phase2g_robot.png'),('/__phase2f_screenshot__/','/__phase2g_screenshot__/'),('screenshots/phase2f/','screenshots/phase2g/')]: app=app.replace(a,b)
modelcall="const model=await addG62Visual('../../data/processed/phase2e/Kiba_Park_Ohashi_G6.2_visual_details_sanitized.glb',THREE,bridgeGroup);"
if modelcall not in app: raise RuntimeError('Missing G6.2 load call')
app=app.replace(modelcall,'const phase2gDetail=addPhase2gDetails(deck.surfaces);'+modelcall,1)
save_old="renderer.domElement.toBlob(async b=>{const r=await fetch('/__phase2g_screenshot__/'+names[viewMode],{method:'POST',body:b});status.textContent=r.ok?'PNG保存: screenshots/phase2g/'+names[viewMode]:'PNG保存失敗'},'image/png')"
save_new="(async()=>{try{const b64=renderer.domElement.toDataURL('image/png').split(',')[1];const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const r=await fetch('/__phase2g_screenshot__/'+names[viewMode],{method:'POST',body:bytes});status.textContent=r.ok?'Screenshot saved: '+names[viewMode]:'Screenshot save failed'}catch(e){status.textContent='Screenshot error: '+e.message}})()"
if save_old not in app: raise RuntimeError('Screenshot handler anchor missing')
app=app.replace(save_old,save_new,1)
app_path.write_text(app,encoding='utf-8')
html_path=web/'index.html'; html=html_path.read_text(encoding='utf-8').replace('Phase 2F','Phase 2G').replace('phase2f','phase2g').replace('Phase 2G 橋面候補','Phase 2G 橋梁ディテール候補').replace('推定橋面</span>','推定橋面</span><span>下面・欄干：寸法推定／衝突なし</span>')
html_path.write_text(html,encoding='utf-8')
params={"phase":"2G","coordinateSystem":"EPSG:6677 local; Three.js x=east, y=estimated T.P. metres, z=-north","parameters":[
{"name":"overall_bridge_length","value":250.0,"unit":"m","class":"documented","basis":"Tokyo Metropolitan Park Association; JCI archive","confidence":"high","usedForGeometry":False},
{"name":"maximum_span","value":96.95,"unit":"m","class":"documented","basis":"Japan Concrete Institute archive","confidence":"high","usedForGeometry":False},
{"name":"pylon_height","value":60.0,"unit":"m","class":"documented_and_asset_extent","basis":"Tokyo park association and Phase 2E GLB vertex extent Y=0..60","confidence":"high for reference, not survey registration","usedForGeometry":False},
{"name":"structure_type","value":"2-span continuous prestressed concrete cable-stayed bridge","class":"documented","basis":"Japan Concrete Institute archive","confidence":"high","usedForGeometry":False},
{"name":"OSM_way_33976871_length","value":174.289,"unit":"m","class":"measured_from_OSM_geometry","basis":"Three projected OSM nodes EPSG:6677","confidence":"high for mapped way only","usedForGeometry":True},
{"name":"Phase_2F_candidate_centerline","value":149.445,"unit":"m","class":"measured_from_candidate_geometry","basis":"132.836m clipped mapped runs + 16.609m linearly interpolated visual gap","confidence":"high for candidate only","usedForGeometry":True},
{"name":"candidate_width","value":4.0,"unit":"m","class":"estimated","basis":"Phase 2F working visual estimate; no survey width","confidence":"low","usedForGeometry":True},
{"name":"deck_height","value":"Phase 2C estimated 1.568..4.940m; gap 2.616..2.140m","unit":"m","class":"estimated","basis":"Navigation surface heights, no bridge deck survey","confidence":"low","usedForGeometry":True},
{"name":"G6.2_registration","value":"translation 0; rotation 0; scale 1 hypothesis","class":"unconfirmed","basis":"EPSG metadata origin matches Phase 2B; axis metadata conflicts with Y-up mesh bounds; no control points","confidence":"low","usedForGeometry":True},
{"name":"G6.2_bounds","value":{"x":[73.868,89.6],"y":[0,60],"z":[-236.018,-47.979]},"unit":"m","class":"measured_from_GLTF_vertices","basis":"Phase 2E sanitized clone, 27 meshes, 356 triangles, no deck","confidence":"high for asset coordinates only","usedForGeometry":True},
{"name":"Phase_2G_underside_thickness","value":0.32,"unit":"m","class":"estimated_visual_prototype","basis":"No structural drawings","confidence":"very_low","usedForGeometry":True},
{"name":"Phase_2G_edge_curb_height","value":0.18,"unit":"m","class":"estimated_visual_prototype","basis":"No dimensional evidence","confidence":"very_low","usedForGeometry":True},
{"name":"Phase_2G_guardrail_height","value":1.05,"unit":"m","class":"estimated_visual_prototype","basis":"Photographic silhouette only; no dimensional survey","confidence":"very_low","usedForGeometry":True}],
"geometryScope":{"sourceOSMWay":"33976871","mappedSurfaceQuads":319,"gapQuadsVisualOnly":1,"unresolvedOverallLengthMetres":100.555,"collisionEnabled":False,"navigationModified":False,"robotTraversalEnabled":False,"detailKinds":["underside","edge curb","guardrail"],"joints":"not modeled; unverified"},
"registration":{"translationMetres":[0,0,0],"rotationDegrees":[0,0,0],"scale":1,"status":"visual hypothesis, no survey control point"}}
(build/'data'/'processed'/'phase2g').mkdir(parents=True,exist_ok=True)
(build/'data'/'processed'/'phase2g'/'bridge_parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Built Phase 2G viewer at {web}')
