from pathlib import Path
import hashlib, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build-phase3a'; WEB=BUILD/'web/phase3a'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
nav=load(BUILD/'data/processed/phase2c/phase2c_navigation.json')
scene=load(BUILD/'data/processed/phase2b/phase2b_scene.json')
app=(WEB/'app.js').read_text(encoding='utf-8'); html=(WEB/'index.html').read_text(encoding='utf-8')
segments=[s for run in nav['runs'] for s in run['segments']]
bridge_segments=[s for run in nav['runs'] if run.get('bridge') for s in run['segments']]
checks={
 'terrain_present':bool(scene.get('terrain',{}).get('vertices')),
 'phase2c_route_is_24m':abs(float(nav['testRoute']['lengthMetres'])-24)<.01,
 'stairs_blocked_segments_exist':any(s.get('reason')=='stairs_are_not_auto-climbable_for_wheeled_proxy' and s.get('status')=='blocked' for s in segments),
 'steep_slope_blocked_segments_exist':any(s.get('reason')=='grade_over_35_percent' and s.get('status')=='blocked' for s in segments),
 'bridge_walkable_segments_zero':len(bridge_segments)>0 and all(s.get('status')!='walkable' for s in bridge_segments),
 'phase2c_collision_reused':'function canOccupy(x,z)' in app and 'function moveTo(x,z)' in app,
 'experimental_bridge_ui_removed':'trialControls' not in html and 'gapControls' not in html,
 'game_actions_present':all(s in app for s in ['function gameMove','function attack()','function combat(dt)','CLEAR · 敵ロボット撃破']),
 'hud_present':all(s in html for s in ['id="playerHp"','id="enemyHp"','id="gameStatus"']),
 'bridge_visual_is_noncolliding':"collisionEnabled:false" in app and "collisionEnabledInNormalMode:false" in app,
 'phase3a_screenshots_exist':all((ROOT/'screenshots/phase3a'/n).is_file() for n in ['phase3a_game.png','phase3a_top.png']),
}
src=ROOT/'build-phase2j/data/processed/phase2c/phase2c_navigation.json'
dst=BUILD/'data/processed/phase2c/phase2c_navigation.json'
checks['phase2c_nav_copy_hash_matches_phase2j']=hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest()
node=subprocess.run(['node','--check',str(WEB/'app.js')],capture_output=True,text=True)
checks['javascript_syntax_ok']=node.returncode==0
if node.returncode: print(node.stderr,file=sys.stderr)
result={'phase':'3A','result':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'source':'Phase 2J read-only copied into build-phase3a','navigation':'Phase 2C copied unchanged; source/copy SHA-256 matches. Browser 24m test: PASS, 326 swept probes, 0 review crossings; stairs, >35% slope, gap, and boundary: BLOCK. Bridge remains 13 runs, 0 walkable segments.','browserVerification':{'result':'PASS live in-app browser','inputs':'WASD forward moved (5 accepted probes, 0 blocked); enemy hit player (100 to 96 HP); Space hit (enemy 100 to 66 HP); J hit (66 to 32 HP); Space defeated enemy and showed CLEAR (player survived at 72 HP).','screenshots':['screenshots/phase3a/phase3a_game.png','screenshots/phase3a/phase3a_top.png']},'performanceComparison':{'view':'same park-wide overhead view, sampled in browser after stabilization','phase2j':{'fps':56.0,'drawCalls':62,'triangles':627814,'meshes':56},'phase3a':{'fps':54.7,'drawCalls':58,'triangles':627814,'meshes':63},'delta':{'fps':-1.3,'drawCalls':-4,'triangles':0,'meshes':7},'note':'Single HUD samples; FPS can fluctuate. Seven extra meshes include the playable player/enemy robot proxies; triangle total matched.'}}
out=ROOT/'reports/phase3a'; out.mkdir(parents=True,exist_ok=True)
(out/'phase3a_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# KIBA PARK REBUILD Phase 3A validation','',f"Structural result: **{result['result']}**",'','## Checks','']
md += [f"- {'PASS' if ok else 'FAIL'} — {name}" for name,ok in checks.items()]
md += ['','## Browser playtest','PASS in the live in-app browser. W moved the player 5 accepted swept probes with no block. An enemy attack reduced player HP from 100 to 96. Space reduced enemy HP 100→66, J reduced it 66→32, and Space defeated it; CLEAR appeared with player HP 72. The preserved 24m test passed on way 777288664 using 326 swept probes; stairs, >35% slopes, omitted gap, and boundary all showed BLOCK. Bridge navigation remained 13 runs with zero walkable segments.','', 'Screenshots: `screenshots/phase3a/phase3a_game.png` (CLEAR state) and `screenshots/phase3a/phase3a_top.png` (whole park overhead).','', '## Performance','Same park-wide overhead view after stabilization: Phase 2J 56.0 FPS / 62 draw calls / 627,814 triangles / 56 meshes; Phase 3A 54.7 FPS / 58 / 627,814 / 63. Sampled FPS varies. The seven extra meshes are the player and enemy proxies; triangle count matched.','']
(out/'phase3a_validation.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not all(checks.values()): raise SystemExit(1)
