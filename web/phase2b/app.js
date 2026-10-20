import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

const status=document.querySelector('#status'),metrics=document.querySelector('#metrics'),error=document.querySelector('#error');
const renderer=new THREE.WebGLRenderer({antialias:false,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.1));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0xd1dcda);document.querySelector('#viewport').prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0xd1dcda);
const camera=new THREE.PerspectiveCamera(43,innerWidth/innerHeight,.1,6000);camera.position.set(440,430,520);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.target.set(0,5,0);controls.maxPolarAngle=Math.PI*.48;
scene.add(new THREE.HemisphereLight(0xffffff,0x65725e,1.25));const sun=new THREE.DirectionalLight(0xfff3dc,1.35);sun.position.set(-250,420,-220);scene.add(sun);
const mat=(color,roughness=.9)=>new THREE.MeshStandardMaterial({color,roughness,side:THREE.DoubleSide});
const terrainMat=mat(0x7eaa70),waterMat=mat(0x53aeb6,.26),buildingMat=mat(0xc3a98a),bridgeMat=mat(0x477e83),pathMats={walk:mat(0xc6b99f),steps:mat(0x92918b),vehicular:mat(0x696d70)};
const group=new THREE.Group();scene.add(group);let debugPoints;
function indexedMesh(vertices,indices,material){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();return new THREE.Mesh(g,material)}
function addRoadGroup(roads,kind,bridges=false){const positions=[],indices=[];for(const r of roads.filter(x=>x.group===kind&&!!x.bridge===bridges)){const base=positions.length/3;for(const s of r.stations)positions.push(...s.slice(0,3),...s.slice(3,6));for(const i of r.indices)indices.push(base+i)}if(indices.length)group.add(indexedMesh(positions,indices,bridges?bridgeMat:pathMats[kind]))}
let groundY=()=>0;
function addFootprints(features,material,offset,extrude=0){const pos=[],idx=[];for(const f of features||[]){const pts=f.points;if(!pts||pts.length<3)continue;const base=pos.length/3,cx=pts.reduce((s,p)=>s+p[0],0)/pts.length,cz=pts.reduce((s,p)=>s+p[2],0)/pts.length;const cy=groundY(cx,cz)+offset;pos.push(cx,cy+extrude,cz);for(const p of pts)pos.push(p[0],groundY(p[0],p[2])+offset+extrude,p[2]);for(let i=0;i<pts.length;i++){idx.push(base,base+1+i,base+1+(i+1)%pts.length);if(extrude){const a=base+1+i,b=base+1+(i+1)%pts.length;const aa=pos.length/3;pos.push(pos[a*3],pos[a*3+1]-extrude,pos[a*3+2],pos[b*3],pos[b*3+1]-extrude,pos[b*3+2]);idx.push(a,aa,b,b,aa,aa+1)}}}if(idx.length)group.add(indexedMesh(pos,idx,material))}
function renderScene(data){const t=data.terrain,v=t.vertices.flatMap(p=>[p[0],p[1],p[2]]),faces=t.faces;const b=data.bounds,nx=t.width,nz=t.height;groundY=(x,z)=>{const u=Math.max(0,Math.min(nx-1,Math.round((x-b[0])/(b[2]-b[0])*(nx-1)))),w=Math.max(0,Math.min(nz-1,Math.round((z-b[1])/(b[3]-b[1])*(nz-1))));return t.vertices[w*nx+u][1]};group.add(indexedMesh(v,faces,terrainMat));
const ids=t.interpolatedIndices||[];const pts=[];for(const i of ids){const p=t.vertices[i];pts.push(p[0],p[1]+.18,p[2])}const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));debugPoints=new THREE.Points(pg,new THREE.PointsMaterial({color:0xff641e,size:1.3,sizeAttenuation:true,depthTest:false}));debugPoints.renderOrder=9;scene.add(debugPoints);debugPoints.visible=document.querySelector('#debug').checked;
for(const k of ['walk','steps','vehicular']){addRoadGroup(data.roads,k);addRoadGroup(data.roads,k,true)}addFootprints(data.features.water,waterMat,.09);addFootprints(data.features.buildings,buildingMat,.10,3.5);
const width=b[2]-b[0],depth=b[3]-b[1],centerX=(b[0]+b[2])/2,centerZ=(b[1]+b[3])/2;controls.target.set(centerX,2,centerZ);camera.position.set(centerX+width*.396,2+depth*.684,centerZ+depth*.972);controls.update();
const demCount=t.heightSource.filter(x=>x.startsWith('dem17_')).length;status.textContent=`1m地形 ${nxFormat(t.width*t.height)}頂点 · DEM1A ${demCount} · 補間/引継ぎ ${ids.length} · 園路 ${data.roads.length} runs`;
}
function nxFormat(n){return n.toLocaleString('ja-JP')}
document.querySelector('#debug').addEventListener('change',e=>{if(debugPoints)debugPoints.visible=e.target.checked});
fetch('../../data/processed/phase2b/phase2b_scene.json').then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}: Phase2B JSONが見つかりません`);return r.json()}).then(renderScene).catch(e=>{error.textContent=`読込エラー: ${e.message}`;status.textContent='表示できません'});
let frames=0,last=performance.now(),fps=0;function loop(now){requestAnimationFrame(loop);controls.update();renderer.render(scene,camera);frames++;if(now-last>=1000){fps=frames*1000/(now-last);frames=0;last=now;let meshes=0;group.traverse(o=>{if(o.isMesh)meshes++});const info=renderer.info;metrics.textContent=`${fps.toFixed(1)} FPS · draw ${info.render.calls} · tris ${info.render.triangles.toLocaleString()} · meshes ${meshes} · DPR ${renderer.getPixelRatio().toFixed(2)}`}}requestAnimationFrame(loop);
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});




