import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, '../..');
const outputRoot = path.resolve(process.env.KIBA_PHASE2E_OUTPUT_ROOT || root);
const sourceRoot = path.resolve(process.env.KIBA_PHASE2E_SOURCE_ROOT || root);
const out = path.join(outputRoot, 'build-phase2e');
const mustReplace = (value, from, to, label) => {
  if (!value.includes(from)) throw new Error(`Phase 2D viewer template changed: ${label}`);
  return value.replace(from, to);
};

await mkdir(out, { recursive: true });
for (const [sourceRel, outputRel] of [['web/phase2d', 'web/phase2e'],
  ['data/processed/phase2b', 'data/processed/phase2b'], ['data/processed/phase2c', 'data/processed/phase2c'],
  ['data/processed/phase2d', 'data/processed/phase2d'], ['data/processed/phase2e', 'data/processed/phase2e']]) {
  await cp(path.join(sourceRoot, sourceRel), path.join(out, outputRel),
    { recursive: true, force: true });
}
await cp(path.join(sourceRoot, 'web/phase2c/vendor'), path.join(out, 'web/phase2e/vendor'),
  { recursive: true, force: true });
const viewerRoot = path.join(out, 'web/phase2e');
const htmlPath = path.join(viewerRoot, 'index.html');
let html = await readFile(htmlPath, 'utf8');
html = html.replaceAll('Phase 2D', 'Phase 2E').replaceAll('Phase 2E 植生景観', 'Phase 2E G6.2統合');
html = html.replace('<span id="vegetationStat"></span>', '<span id="vegetationStat"></span><span id="bridgeStatus">G6.2読込中 · 見た目専用 · 橋面高さ未照合</span>');
html = html.replace('<button id="viewAbove">上空視点</button>', '<button id="viewAbove">上空視点</button><button id="viewBridge">橋梁地上視点</button>');
await writeFile(htmlPath, html, 'utf8');

let app = await readFile(path.join(viewerRoot, 'app.js'), 'utf8');
app = mustReplace(app, "import { OrbitControls } from './vendor/OrbitControls.js';",
  "import { OrbitControls } from './vendor/OrbitControls.js';\nimport { addG62Visual } from './g62-loader.js';", 'imports');
app = mustReplace(app, 'const root=new THREE.Group(),navGroup=new THREE.Group(),foliageGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup);',
  'const root=new THREE.Group(),navGroup=new THREE.Group(),foliageGroup=new THREE.Group(),bridgeGroup=new THREE.Group();scene.add(root,navGroup,foliageGroup,bridgeGroup);', 'scene groups');
app = mustReplace(app, "if(mode==='top'){controls.enabled=true;controls.target.set(cx,2,cz);camera.position.set(cx+w*.396,2+d*.684,cz+d*.972);$('#viewStatus').textContent='上空視点';}else{controls.enabled=false;if(robotPos){const h=robot.rotation.y;camera.position.set(robotPos.x+Math.sin(h)*4.2,robotPos.y+2.0,robotPos.z+Math.cos(h)*4.2);camera.lookAt(robotPos.x-Math.sin(h)*2,robotPos.y+1.1,robotPos.z-Math.cos(h)*2)}$('#viewStatus').textContent='ロボット視点';}updateVegetationLOD()",
  "if(mode==='bridge'){controls.enabled=false;controls.target.set(82,8,-142);camera.position.set(118,14,-102);camera.lookAt(82,10,-142);$('#viewStatus').textContent='橋梁地上視点';updateVegetationLOD();return;}if(mode==='top'){controls.enabled=true;controls.target.set(cx,2,cz);camera.position.set(cx+w*.396,2+d*.684,cz+d*.972);$('#viewStatus').textContent='上空視点';}else{controls.enabled=false;if(robotPos){const h=robot.rotation.y;camera.position.set(robotPos.x+Math.sin(h)*4.2,robotPos.y+2.0,robotPos.z+Math.cos(h)*4.2);camera.lookAt(robotPos.x-Math.sin(h)*2,robotPos.y+1.1,robotPos.z-Math.cos(h)*2)}$('#viewStatus').textContent='ロボット視点';}updateVegetationLOD()", 'bridge camera');
app = mustReplace(app, "]).then(([a,b,c])=>render(a,b,c)).catch(e=>{error.textContent=`読込エラー: ${e.message}`;status.textContent='表示できません'});",
  "]).then(async ([a,b,c])=>{render(a,b,c);const model=await addG62Visual('../../data/processed/phase2e/Kiba_Park_Ohashi_G6.2_visual_details_sanitized.glb',THREE,bridgeGroup);$('#bridgeStatus').textContent=`G6.2表示 ${model.meshes}メッシュ · 見た目専用 · 橋面高さ未照合 · 橋梁13ラン要確認`;status.textContent='GLBは座標候補に登録 · Phase 2Cの橋梁移動面は推定/要確認のまま';}).catch(e=>{error.textContent=`読込エラー: ${e.message}`;status.textContent='表示できません'});", 'asset load');
app = mustReplace(app, "$('#viewAbove').addEventListener('click',()=>setView('top'));$('#viewRobot')",
  "$('#viewAbove').addEventListener('click',()=>setView('top'));$('#viewBridge').addEventListener('click',()=>setView('bridge'));$('#viewRobot')", 'view button');
app = mustReplace(app, 'foliageGroup.traverse(o=>{if(o.isMesh)meshes++});perf.textContent=',
  'foliageGroup.traverse(o=>{if(o.isMesh)meshes++});bridgeGroup.traverse(o=>{if(o.isMesh)meshes++});perf.textContent=', 'mesh accounting');
await writeFile(path.join(viewerRoot, 'app.js'), app, 'utf8');
await cp(path.join(scriptDir, 'g62-loader.js'), path.join(viewerRoot, 'g62-loader.js'), { force: true });
await cp(path.join(sourceRoot, 'reports/phase2e'), path.join(out, 'reports/phase2e'), { recursive: true, force: true });
console.log(`Phase 2E viewer assembled: ${out}`);
