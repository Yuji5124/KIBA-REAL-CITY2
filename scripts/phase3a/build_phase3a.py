from pathlib import Path
import shutil, re

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'build-phase2j'; BUILD=ROOT/'build-phase3a'
if not SOURCE.is_dir(): raise SystemExit('Phase 2J build is missing.')
if BUILD.exists(): shutil.rmtree(BUILD)
shutil.copytree(SOURCE,BUILD)
web=BUILD/'web/phase2j'; web.rename(BUILD/'web/phase3a'); web=BUILD/'web/phase3a'
html=(web/'index.html').read_text(encoding='utf-8')
for a,b in [('木場公園 Phase 2J · Bridge scope','KIBA PARK · Phase 3A'),('木場公園 · Phase 2J 橋梁範囲調査','木場公園 · Phase 3A ロボットアクション'),('Phase 2J PNG保存','画面を保存'),('24m移動テスト','既存24m移動テスト'),('推定橋面候補を表示（通行不可）','推定橋梁表示（通行不可）'),('移動判定レイヤーを表示','DEV衝突・移動判定を表示'),('phase2j_top.png','phase3a_top.png'),('phase2j_bridge.png','phase3a_top.png'),('phase2j_side.png','phase3a_top.png'),('phase2j_robot.png','phase3a_game.png')]: html=html.replace(a,b)
html=re.sub(r'<fieldset id="(?:trialControls|gapControls|scopeEvidence)">.*?</fieldset>','',html,flags=re.S)
html=html.replace('<button id="viewRobot">ロボット視点</button>','<button id="viewRobot">ゲームカメラ</button>')
html=html.replace('<button id="viewBridge">橋梁地上視点</button><button id="viewSide">橋梁側面</button>','')
html=html.replace('<button id="test">既存24m移動テスト</button>','<button id="test">既存24m移動テスト</button><button id="attack">攻撃（Space / J）</button><button id="restart">再開（R）</button>')
html=html.replace('操作: WASD / 矢印キー · マウスドラッグで上空視点を移動 · ホイールで拡大縮小','操作: WASDで移動 · Space / Jで攻撃 · 園路上で敵1体を撃破')
html=html.replace('<output id="testResult">','<output id="gameStatus">戦闘エリアを準備中…</output><div id="health"><span>PLAYER</span><meter id="playerHp" min="0" max="100" value="100"></meter><span id="playerHpText">100 HP</span><span>ENEMY</span><meter id="enemyHp" min="0" max="100" value="100"></meter><span id="enemyHpText">100 HP</span></div><output id="testResult">')
(web/'index.html').write_text(html,encoding='utf-8')
css=(web/'style.css').read_text(encoding='utf-8')+'\n#health{display:grid;grid-template-columns:58px 1fr 55px;align-items:center;gap:4px;font-size:11px;color:#344b42}#health meter{width:100%;height:12px;accent-color:#55c782}#enemyHp{accent-color:#ed6d59}#gameStatus{padding:6px 8px;border-radius:7px;background:#eaf4ed;color:#284a3a;font-weight:650}#hud{width:min(410px,calc(100vw - 24px));min-width:0;padding:10px 12px;top:12px;left:12px;gap:5px}#vegetationStat,#bridgeStatus,#viewStatus{display:none}\n'
(web/'style.css').write_text(css,encoding='utf-8')
js=(web/'app.js').read_text(encoding='utf-8')
# The scene's async data loader can call render as soon as the module's first
# Promise settles; put simulation state before that loader to avoid TDZ access.
js=js.replace('const materials={deck:', "const gameGroup=new THREE.Group();scene.add(gameGroup);const game={active:false,paused:false,clear:false,over:false,playerHp:100,enemyHp:100,attackCooldown:0,enemyAttackCooldown:0,speed:2,enemy:null,forward:{x:0,z:-1},flash:0};addEventListener('error',e=>{const n=$('#error');if(n)n.textContent='実行エラー: '+e.message});\nconst materials={deck:")
# Remove bridge experiment controls from the game-facing UI/listeners; normal Phase 2C collision remains the only game movement path.
js=re.sub(r"\$\('#trialMode'\).*?\$\('#trialReset'\)\.addEventListener\('click',resetTrial\);",'',js)
js=re.sub(r"\$\('#gapCandidateToggle'\).*?\$\('#gapReverse'\)\.addEventListener\('click',\(\)=>runGapTraversal\(-1\)\);",'',js)
js=js.replace("evidenceGroup.visible=true;document.querySelector('#osmTrace').addEventListener('change',e=>evidenceGroup.visible=e.target.checked)","evidenceGroup.visible=false")
js=js.replace("$('#viewAbove').addEventListener('click',()=>setView('top'));$('#viewBridge').addEventListener('click',()=>setView('bridge'));$('#viewSide').addEventListener('click',()=>setView('side'));$('#deckToggle').addEventListener('change',e=>deckGroup.visible=e.target.checked);$('#viewRobot').addEventListener('click',()=>setView('robot'));$('#viewAbove').addEventListener('click',()=>setView('top'));$('#viewBridge').addEventListener('click',()=>setView('top'));$('#viewSide').addEventListener('click',()=>setView('side'));", "$('#viewAbove').addEventListener('click',()=>setView('top'));$('#deckToggle').addEventListener('change',e=>deckGroup.visible=e.target.checked);$('#viewRobot').addEventListener('click',()=>setView('robot'));")
js=re.sub(r"\$\('#viewBridge'\)\.addEventListener\('click',\(\)=>setView\('[^']+'\)\);",'',js)
js=re.sub(r"\$\('#viewSide'\)\.addEventListener\('click',\(\)=>setView\('[^']+'\)\);",'',js)
js=js.replace("error.textContent=`読込エラー: ${e.message}`", "error.textContent=`読込エラー: ${e.stack||e.message}`")
js=js.replace('camera.position.set(robotPos.x+Math.sin(h)*4.2,robotPos.y+2.0,robotPos.z+Math.cos(h)*4.2)','camera.position.set(robotPos.x+Math.sin(h)*7.2,robotPos.y+3.2,robotPos.z+Math.cos(h)*7.2)')
js=js.replace('px=robotPos.x+Math.sin(h)*4.2,pz=robotPos.z+Math.cos(h)*4.2','px=robotPos.x+Math.sin(h)*7.2,pz=robotPos.z+Math.cos(h)*7.2')
js=js.replace('camera.position.lerp(new THREE.Vector3(px,robotPos.y+2.0,pz),.18)','camera.position.lerp(new THREE.Vector3(px,robotPos.y+3.2,pz),.18)')
js=js.replace('const step=Math.min(dt,d-1.25)','const step=Math.min(.62*dt,d-1.25)')
js=js.replace('game.enemyAttackCooldown=1.1;game.playerHp=Math.max(0,game.playerHp-10)','game.enemyAttackCooldown=1.35;game.playerHp=Math.max(0,game.playerHp-6)')
game=r'''
function routeAt(s){const p=testRoute.points;for(let i=1;i<p.length;i++){const a=p[i-1],b=p[i],d=Math.hypot(b[0]-a[0],b[2]-a[2]);if(s<=d){const t=d?s/d:0,dx=b[0]-a[0],dz=b[2]-a[2];return{x:a[0]+dx*t,y:a[1]+(b[1]-a[1])*t,z:a[2]+dz*t,h:Math.atan2(-dx,-dz)}}s-=d}const q=p.at(-1);return{x:q[0],y:q[1],z:q[2],h:Math.PI}}
function bot(color){const g=new THREE.Group(),mat=(c)=>new THREE.MeshStandardMaterial({color:c,roughness:.55,metalness:.15}),body=new THREE.Mesh(new THREE.BoxGeometry(.86,.42,.98),mat(color)),head=new THREE.Mesh(new THREE.BoxGeometry(.48,.32,.48),mat(0xe2edf0)),visor=new THREE.Mesh(new THREE.BoxGeometry(.28,.06,.035),mat(0x55f0e8));body.position.y=.54;head.position.set(0,.94,-.08);visor.position.set(0,.96,-.33);g.add(body,head,visor);for(const x of [-.52,.52]){let a=new THREE.Mesh(new THREE.BoxGeometry(.22,.5,.27),mat(color));a.position.set(x,.54,-.06);g.add(a);let l=new THREE.Mesh(new THREE.BoxGeometry(.25,.34,.3),mat(0x354047));l.position.set(x*.5,.17,.09);g.add(l)}return g}
function hud(msg){const ph=$('#playerHp');if(!ph)return;ph.value=game.playerHp;$('#enemyHp').value=game.enemyHp;$('#playerHpText').textContent=game.playerHp+' HP';$('#enemyHpText').textContent=game.enemyHp?game.enemyHp+' HP':'撃破';$('#gameStatus').textContent=msg|| (game.clear?'CLEAR · 敵ロボット撃破':game.over?'GAME OVER · Rで再開':'戦闘中 · 敵まで '+(game.enemy?Math.hypot(robotPos.x-game.enemy.position.x,robotPos.z-game.enemy.position.z).toFixed(1):'–')+'m')}
function restartGame(){if(!robot||!testRoute)return;game.playerHp=100;game.enemyHp=100;game.clear=game.over=false;game.active=true;game.attackCooldown=game.enemyAttackCooldown=0;const p=routeAt(9),q=routeAt(14);robotPos={x:p.x,y:p.y,z:p.z};robot.position.set(p.x,p.y,p.z);robot.rotation.y=p.h;game.forward={x:-Math.sin(robot.rotation.y),z:-Math.cos(robot.rotation.y)};if(game.enemy)gameGroup.remove(game.enemy);game.enemy=bot(0xc6533f);game.enemy.position.set(q.x,q.y,q.z);game.enemy.rotation.y=q.h;gameGroup.add(game.enemy);game.paused=false;hud('戦闘開始 · 園路上の戦闘区間で敵ロボットを撃破');if(viewMode!=='robot')setView('robot')}
function attack(){if(!game.active||game.attackCooldown>0)return;game.attackCooldown=.42;game.flash=.12;const e=game.enemy;if(!e)return;const dx=e.position.x-robotPos.x,dz=e.position.z-robotPos.z,d=Math.hypot(dx,dz)||1,dot=dx/d*game.forward.x+dz/d*game.forward.z;if(d<5.3&&dot>.48){game.enemyHp=Math.max(0,game.enemyHp-34);if(!game.enemyHp){e.visible=false;game.clear=true;game.active=false;hud('CLEAR · 敵ロボット撃破')}else hud('命中 · 敵HP '+game.enemyHp)}else hud('攻撃空振り · 距離 '+d.toFixed(1)+'m')}
function gameMove(x,z,dt){if(game.clear||game.over)return;const n=Math.hypot(x,z);if(!n)return;const dx=x/n*game.speed*dt,dz=z/n*game.speed*dt;if(moveTo(robotPos.x+dx,robotPos.z+dz)){robot.rotation.y=Math.atan2(-dx,-dz);game.forward={x:-Math.sin(robot.rotation.y),z:-Math.cos(robot.rotation.y)}}}
function combat(dt){if(!game.active||game.paused||!game.enemy)return;game.attackCooldown=Math.max(0,game.attackCooldown-dt);game.enemyAttackCooldown=Math.max(0,game.enemyAttackCooldown-dt);const e=game.enemy,dx=robotPos.x-e.position.x,dz=robotPos.z-e.position.z,d=Math.hypot(dx,dz);if(d>1.45){const step=Math.min(.32*dt,d-1.25),n=Math.max(1,Math.ceil(step/.07));for(let i=1;i<=n;i++){const x=e.position.x+dx/d*step*i/n,z=e.position.z+dz/d*step*i/n,h=canOccupy(x,z);if(!h.ok)break;e.position.set(x,h.y,z)}e.rotation.y=Math.atan2(-dx,-dz)}else if(game.enemyAttackCooldown<=0){game.enemyAttackCooldown=3;game.playerHp=Math.max(0,game.playerHp-4);hud('被弾 · PLAYER HP '+game.playerHp);if(!game.playerHp){game.over=true;game.active=false;hud('GAME OVER · Rで再開')}}if(game.flash>0){game.flash-=dt;robot.children[0].material.emissive.setHex(0x17605d)}else robot.children[0].material.emissive.setHex(0)}
const phase2JTest=runAutoTest;runAutoTest=function(){game.paused=true;phase2JTest();game.paused=false;restartGame()};$('#attack').addEventListener('click',attack);$('#restart').addEventListener('click',restartGame);
'''
anchor="const keys=new Set();addEventListener('keydown',e=>{if(['w','a','s','d','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();keys.add(e.key)}});"
if anchor not in js: raise SystemExit('Phase 2J input loop anchor missing')
js=js.replace(anchor,game+"\nconst keys=new Set();addEventListener('keydown',e=>{if(['w','a','s','d','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();keys.add(e.key)}if(e.code==='Space'||e.key.toLowerCase()==='j'){e.preventDefault();attack()}if(e.key.toLowerCase()==='r')restartGame()});")
js=js.replace('trialMode?moveTrial(x/n*2*dt,z/n*2*dt):moveTo(robotPos.x+x/n*2*dt,robotPos.z+z/n*2*dt)','trialMode?moveTrial(x/n*2*dt,z/n*2*dt):gameMove(Math.cos(robot.rotation.y)*x+Math.sin(robot.rotation.y)*z,-Math.sin(robot.rotation.y)*x+Math.cos(robot.rotation.y)*z,dt)')
js=js.replace('if(now-lastLod>400){updateVegetationLOD();lastLod=now}','combat(dt);if(now-lastLod>400){updateVegetationLOD();lastLod=now}')
js=js.replace('deckGroup.traverse(o=>{if(o.isMesh)meshes++});','deckGroup.traverse(o=>{if(o.isMesh)meshes++});gameGroup.traverse(o=>{if(o.isMesh)meshes++});')
js=js.replace("setView('top');$('#vegetationStat')","setView('robot');restartGame();$('#vegetationStat')")
js=js.replace("phase2j_top.png","phase3a_top.png").replace("phase2j_bridge.png","phase3a_top.png").replace("phase2j_side.png","phase3a_top.png").replace("phase2j_robot.png","phase3a_game.png").replace("'/__phase2j_screenshot__/","'/__phase3a_screenshot__/")
js=js.replace('· 移動 ${moveStats.ok} · 拒否 ${moveStats.blocked}`','· 移動 ${moveStats.ok} · 拒否 ${moveStats.blocked} · ${game.clear?\'CLEAR\':game.over?\'GAME OVER\':\'敵HP \'+game.enemyHp}`')
(web/'app.js').write_text(js,encoding='utf-8')
print('Phase 3A viewer/data generated:',web)
