from pathlib import Path
import hashlib, json, math, struct, ast
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build-phase2j'; DATA=BUILD/'data/processed/phase2j/bridge_scope_analysis.json'
A=json.loads(DATA.read_text(encoding='utf-8'))
ALIGNLEN=A['g62']['xyzDimensionsMetres'][2]
nearest=A['alignmentAudit']['phase2gLateralNearestDistanceToOSM33976871Metres']
station=A['alignmentAudit']['towerApproxStationFromSharedJunctionMetres']
route1=A['osm']['northToSouthRouteLengthsMetres']['north_terminal_to_6400941151_via_598428792']
route2=A['osm']['northToSouthRouteLengthsMetres']['north_terminal_to_6400941152_via_683394375']
display=A['phase2f']['displayedWay33976871PlusGapMetres']
outline=A['osm']['bridgeFootprint']
nav=BUILD/'data/processed/phase2c/phase2c_navigation.json'
nav_h=ROOT/'build-phase2h/data/processed/phase2c/phase2c_navigation.json'
nav_sha=hashlib.sha256(nav.read_bytes()).hexdigest()
assert nav_sha==hashlib.sha256(nav_h.read_bytes()).hexdigest()=='2a127eff41dce83fb98b3fc725bcc130d060495f3b2c2ffcc27e65bca7578b55'
osm=A['osm']; trunk=osm['trunk']; a,b=osm['southBranches']
assert trunk['wayId']=='33976871' and trunk['tags'].get('bridge')=='yes'
assert a['wayId']=='598428792' and a['tags'].get('bridge')=='yes'
assert b['wayId']=='683394375' and b['tags'].get('bridge')=='yes'
assert trunk['nodeRefs'][0]==a['nodeRefs'][-1]==b['nodeRefs'][0]==osm['sharedJunctionNode']
assert abs(trunk['lengthProjectedMetres']-174.2894865508546)<.002
assert 251<osm['northToSouthRouteLengthsMetres']['north_terminal_to_6400941151_via_598428792']<253
assert 250<osm['northToSouthRouteLengthsMetres']['north_terminal_to_6400941152_via_683394375']<252
assert osm['bridgeFootprint']['closed'] and osm['bridgeFootprint']['nodeCount']==47
assert 248<osm['bridgeFootprint']['northSouthExtentProjectedMetres']<251
assert A['definitionConflict']['differenceMetres']==64
assert A['phase2f']['displayedWay33976871PlusGapMetres']==149.445
assert abs(A['phase2f']['wayLengthOutsideDisplayedCandidateMetres']-24.844)<.01
assert abs(A['derivedComparisonsMetres']['250MinusPhase2f']-100.555)<1e-6
assert A['g62']['deckMeshPresent'] is False
assert 0.3<A['alignmentAudit']['phase2gLateralNearestDistanceToOSM33976871Metres']<.4
assert A['navigationPreserved'] and A['productionNavigationModified'] is False
assert A['bridgeRunStates']=={'review':8,'blocked':5,'walkable':0}
app=(BUILD/'web/phase2j/app.js').read_text(encoding='utf-8')
ast.parse((ROOT/'scripts/phase2j/build_phase2j.py').read_text(encoding='utf-8'))
ast.parse(Path(__file__).read_text(encoding='utf-8'))
assert 'drawPhase2jEvidence(evidence)' in app and 'collisionEnabled:false' in app
assert "'/__phase2j_screenshot__/" in app

shots={}
for view in ('top','bridge','side','robot'):
    p=ROOT/f'screenshots/phase2j/phase2j_{view}.png'
    raw=p.read_bytes(); assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    w,h=struct.unpack('>II',raw[16:24]); assert (w,h)==(1280,720)
    shots[view]={'path':str(p),'width':w,'height':h,'bytes':len(raw),'capturedInActualBrowser':True}

comparisons={}
font_path=Path('C:/Windows/Fonts/meiryo.ttc')
font=ImageFont.truetype(str(font_path),22) if font_path.exists() else ImageFont.load_default()
for view in ('top','bridge','side','robot'):
    old=Image.open(ROOT/f'screenshots/phase2i/phase2i_{view}.png').convert('RGB')
    new=Image.open(ROOT/f'screenshots/phase2j/phase2j_{view}.png').convert('RGB')
    assert old.size==new.size==(1280,720)
    canvas=Image.new('RGB',(2560,766),(236,242,239)); draw=ImageDraw.Draw(canvas)
    draw.text((14,9),f'Phase 2I · {view} · DEV gap candidate ON',fill=(34,67,58),font=font)
    draw.text((1294,9),f'Phase 2J · {view} · candidate OFF, OSM plan traces ON',fill=(34,67,58),font=font)
    canvas.paste(old,(0,46)); canvas.paste(new,(1280,46))
    dest=ROOT/f'screenshots/phase2j/phase2j_compare_{view}.png'
    canvas.save(dest,optimize=True)
    comparisons[view]={'path':str(dest),'width':2560,'height':766,'phase2iState':'DEV candidate ON','phase2jState':'candidate OFF; OSM traces ON'}

perf={'baselinePhase2h':{
 'top':[60.1,62,629090,58],'bridge':[53.2,50,554052,58],'side':[50.2,51,554064,58],'robot':[49.0,49,630604,58]},
 'phase2jObserved':{
 'top':[55.3,62,627814,56],'bridge':[60.1,50,552776,56],'side':[50.2,44,552264,56],'robot':[60.1,53,630604,58]},
 'metricOrder':['FPS','drawCalls','triangles','sceneMeshes'],
 'note':'Phase 2J measurements were read from the live browser HUD; robot view used the isolated Phase 2H estimated trial surface. FPS varies with LOD and browser scheduling. This is not a controlled benchmark.'}

report={
 'phase':'2J','result':'PASS_RESEARCH_ONLY_NO_ADDITIONAL_BRIDGE_MESH',
 'publicLengthDefinitionConflict':A['definitionConflict'],
 'publicReferences':A['publicReferences'],
 'osmTopology':{'trunkWay':trunk,'southBranches':[a,b],'northToSouthRoutes':osm['northToSouthRouteLengthsMetres'],
  'bridgeFootprint':osm['bridgeFootprint'],'unionEdgeLengthMetres':osm['threeArmUnionEdgeLengthMetres']},
 'extentComparisons':{'phase2F':A['phase2f'],'g62':A['g62'],'alignmentAudit':A['alignmentAudit'],'derivedComparisonsMetres':A['derivedComparisonsMetres']},
 'finding':A['conclusion'],
 'navigation':{'sha256':nav_sha,'sameAsPhase2H':True,'phase2cBridgeRuns':A['bridgeRunStates'],'normalMode':'blocked; DEV connection remains off','sourcePhase2CModified':False},
 'browser':{'url':'http://127.0.0.1:8783/web/phase2j/','views':['top','bridge','side','robot'],'normalModeConfirmedAtEnd':True,
  'OSM plan overlays':'visible; line/footprint color-coded, display Y-offset only; no bridge deck height/collision','screenshots':shots,
  'phaseComparisonImages':comparisons,
  '24m park movement regression':'PASS · way 777288664 · 326 swept probes · 0 review crossings · stairs / >35% / gap / boundary BLOCK'},
 'performance':perf,
 'nextEvidenceNeeded':['As-built general arrangement and longitudinal section with explicit 250m endpoints and scope definition.','Deck survey or georeferenced control points tying the 186m structural length and 96.95m span to EPSG:6677.','Plan/profile of both southern branches and the north approach, plus the pylon station and span endpoints.','Authoritative bridge width definitions/sections; technical publication widths (10.8–25.8m standard, 8.228m split) conflict in scope with Phase 2F/I 4m working estimate.','Current orthophoto/LiDAR or total-station/GNSS survey around the clipped boundary approach and the two south landings.'],
 'limitations':['No authoritative source located reconciles 250m and 186m measurement scopes. The likely overall-route vs structural-span interpretation is plausible but still an inference.','The OSM Y-shaped network and approximately 251–252m north-to-south route lengths explain the scale of the 250m value, but OSM geometry is not an as-built survey.','G6.2 is a visual-only tower/cable model with no deck, uses identity placement without survey control, and has conflicting axis metadata. Its 188.039m z-bound is mesh/cable extent, not verified deck length.','The ±0.34m pylon-axis-to-trunk proximity is a local plan comparison only; longitudinal station is asymmetric relative to the raw trunk endpoints and does not validate the 96.95m span.','No Phase 2C navigation, Phase 2I DEV candidate, raw OSM/DEM, G6.2 source, or earlier phase deliverable was changed by Phase 2J.']
}
(ROOT/'reports/phase2j/phase2j_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

lines=['# KIBA PARK REBUILD Phase 2J — 橋梁範囲調査','',
 '## 結論','',A['conclusion'],'',
 '資料値の250mと186mには64mの差がある。都の公園管理計画/JCIアーカイブは3地区を結ぶ橋の全長を250mと記し、1995年のPC建協技術資料は2径間連続PC斜張橋の橋長を186.0m、最大スパン97.0m、標準幅10.8–25.8m、分離部8.228mと記す。JCIの最大支間96.95mと主塔高60mはそれぞれ公開資料の丸め違いと整合する。測定端点・取付部の扱いは資料上で確認できず、250mがアクセス歩道込み、186mが構造物長という説明は推定としてのみ扱う。', '',
 '## OSMトポロジーと距離','',
 '| 要素 | OSM/測定値 | 位置・読み方 |','|---|---:|---|',
 f"| 主線 way 33976871 | {trunk['lengthProjectedMetres']:.3f}m | 3ノード、bridge=yes / footway。共有節点から北側端へ |",
 f"| 南側分岐 way 598428792 | {a['lengthProjectedMetres']:.3f}m | 主線の共有節点からnode {a['nodeRefs'][0]}へ |",
 f"| 南側分岐 way 683394375 | {b['lengthProjectedMetres']:.3f}m | 主線の共有節点からnode {b['nodeRefs'][-1]}へ |",
 f"| 北端→南側端の経路 | {route1:.3f}m / {route2:.3f}m | 各分岐を別々に通る2経路。250mに近いが現況測量値ではない |",
 f"| OSM橋梁外形 way 745579214 | {outline['northSouthExtentProjectedMetres']:.2f}×{outline['eastWestExtentProjectedMetres']:.2f}m | 47ノードの閉ループ。外形範囲であり床版線ではない |",
 '',
 '3つのbridge=yes歩道はnode `6980957124`で分岐し、OSM橋梁外形の南北範囲は約249m。これは橋が単一直線ではなく、北側の主線と南側二方向の枝を持つ可能性を示す。北端から各南側端へのOSM経路長は約251.1mと252.3mで、公開250m値と近い。OSMは編集地図であり、測量・竣工図ではないため、構造端点を確定しない。', '',
 '## 250m差の分解','',
 f"Phase 2Fの149.445mはway 33976871の公園内クリップ済み132.836mと16.609mの表示専用ギャップ補間の合計。raw way自体は174.289mなので、クリップ表示から外れた同一way区間は約24.844m。さらに独立した二本の南側枝が約76.808mと77.975mある。従って`250 - 149.445 = 100.555m`は算術残差であり、単一の未制作区間の長さ・位置ではない。枝を各々一つずつ通る全ルートは251.098m/252.264mだが、公表値との1.098m/2.264m差は丸め・端点定義・地図線形の差かもしれず、根拠なく補正しない。", '',
 'Phase 2Iで特定した16.609mギャップは公園ポリゴンの境界クリップによる。これは250m全体の差や分岐形状とは別の問題である。Phase 2Cは境界外線分を除き、二本のRunを自動接続していない。', '',
 '## G6.2・主塔・支間の照合','',
 f"G6.2は主塔2、横梁1、ケーブル24の27メッシュで、橋面メッシュはない。モデルのZ方向外形は{ALIGNLEN:.3f}m、主塔の高さは60m。Z範囲は支線ケーブルを含むメッシュ外形であり、デッキの橋長とみなせない。モデルは測量基準点なしの恒等配置仮説で、軸メタデータも頂点配置と矛盾する。",
 f"ローカル座標でOSM主線と主塔中心軸の最近距離は約{nearest:.3f}mで、平面上の横位置は近い。一方、主塔位置はOSM共有節点から主線station約{station:.3f}m、北端まで約{trunk['lengthProjectedMetres']-station:.3f}mにあり、96.95m最大支間を照合できない。デッキ両端と支承位置がモデルにないため、スパン割り・橋の北端・分岐側接合点は未確定。",
 '',
 '## 根拠区分','',
 '| 項目 | 値/観察 | 分類 |','|---|---|---|',
 '| 全長 | 250m | 公開資料値・測定端点未定義 |',
 '| 橋長 | 186.0m | 公開技術資料値・250mとの範囲定義未照合 |',
 '| 最大支間 | 96.95m / 97.0m | 公開資料値（精密値/丸め） |',
 '| 主塔高 | 60m | 公開資料値。G6.2形状にも60m高があるが測量照合なし |',
 f"| way 33976871 | {trunk['lengthProjectedMetres']:.3f}m | OSMからEPSG:6677に投影した線形長 |",
 f"| Phase 2F表示候補 | {display:.3f}m | クリップ済み主線＋視覚ギャップ補完。構造長ではない |",
 f"| Phase 2Fの4m幅 | 4m | 推定値。技術資料の幅と適用範囲が不整合 |",
 f"| G6.2外形 | {ALIGNLEN:.3f}m | モデルの頂点外形。橋長ではない |",
 '| 南側二本の枝と外形 | 76.808m、77.975m、閉外形約59×249m | OSMタグ/ジオメトリ。竣工測量ではない |',
 '| 250m−149.445m | 100.555m | 算術残差。位置未確定・単一区間ではない |',
 '',
 '## 実ブラウザーと描画負荷','',
 'Phase 2J専用URLで上空・橋梁地上・側面・ロボット視点を確認し、OSM主線・分岐・外形を標高なしの点線オーバーレイで表示した。通常モードに戻して終了し、Phase 2Cの橋梁は通行不可、Phase 2I DEV接続候補はOFF。24m公園園路テストは326 swept probes、要確認通過0、階段・35%超・ギャップ・境界BLOCKでPASS。ロボット視点だけPhase 2H実験レイヤーを使った撮影後、通常モードへ復帰した。', '',
 '| 視点 | Phase 2H基準 FPS / draw / tris / meshes | Phase 2J観測 FPS / draw / tris / meshes |','|---|---:|---:|',
 '| 上空 | 60.1 / 62 / 629,090 / 58 | 55.3 / 62 / 627,814 / 56 |',
 '| 橋梁地上 | 53.2 / 50 / 554,052 / 58 | 60.1 / 50 / 552,776 / 56 |',
 '| 側面 | 50.2 / 51 / 554,064 / 58 | 50.2 / 44 / 552,264 / 56 |',
 '| ロボット | 49.0 / 49 / 630,604 / 58 | 60.1 / 53 / 630,604 / 58 |',
 '',
 '画面HUDの瞬間値であり、視錐台、植生LOD、操作・ブラウザー負荷で変動する。ロボット視点はPhase 2Hの推定Run上から取得し、通常モードの歩行可能性を示していない。', '',
 '### 保存画像と比較','',
 '- [上空](../../screenshots/phase2j/phase2j_top.png)','- [橋梁地上](../../screenshots/phase2j/phase2j_bridge.png)','- [側面](../../screenshots/phase2j/phase2j_side.png)','- [ロボット](../../screenshots/phase2j/phase2j_robot.png)','',
 'Phase 2I側はDEV接続候補ONで保存された既存画像、Phase 2J側はDEV接続候補OFF・OSM平面トレースON。完全な同一レイヤー条件の性能比較ではなく、表示レイヤーの差を確認する画像。',
 '| 視点 | 比較画像 |','|---|---|',
 '| 上空 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_top.png) |','| 橋梁地上 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_bridge.png) |','| 側面 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_side.png) |','| ロボット | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_robot.png) |','',
 '## 次に必要な根拠','',
 '1. 250m記載の測定端点と取付部を示す整備計画図または竣工一般図。186mの構造端点、両径間長、支間割りを照合できる断面・縦断図。','2. EPSG:6677測量基準点を持つ竣工座標またはGNSS/トータルステーション点（塔中心、桁端、支承、北側端、南側二分岐の接合部）。','3. 二本の南側枝と北側取付部の橋面縦断・幅員・高さを示す平面/縦断/横断図。PC技術資料の10.8–25.8m、8.228mの幅がどの部分に対応するかの説明。','4. クリップ境界付近と南側端部の現況航空写真・LiDARまたは現地測量。OSMは形状候補の追跡には有用だが高さや構造端点の根拠にはならない。','',
 '根拠不足のためPhase 2Jでは橋梁メッシュを追加していない。Phase 1〜2I、rawデータ、Phase 2Cナビ、元G6.2、KIBA-REAL-CITY-mainには書き込みを行っていない。', '',
 '## 再生成・検証・起動（Windows PowerShell）','',
 'Phase 2Iの保存済みビルド（`build-phase2i`）があるクローンのルートで実行する。Phase 2Iの再生成は不要。', '',
 '```powershell',r'cd C:\Users\hp\Desktop\KIBA-REAL-CITY',r'python scripts\phase2j\build_phase2j.py',r'python scripts\phase2j\verify_phase2j.py',r'python scripts\phase2j\serve_phase2j.py','```','',
 '`http://127.0.0.1:8783/web/phase2j/` を開く。OSMオーバーレイは「OSM線形・橋梁外形を表示」で切替できる。高さ・デッキ・衝突判定のレイヤーではない。', '',
 '## 参照','',
 '- [東京都建設局・木場公園マネジメントプラン](https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/070328kbetsumpkiba) — 3ゾーンを連絡する全長250m、主塔高60m。',
 '- [日本コンクリート工学会・木場公園大橋](https://www.jci-net.or.jp/photo_60/archive/detail_db.php?id=168&page=6) — 250m、最大支間96.95m、2径間連続PC斜張橋。',
 '- [プレストレスト・コンクリート建設業協会・1995技術資料PDF](https://jpci.or.jp/data/pc-seminar/text/023_pc-seminar-text_199502.pdf) — 木場公園橋、橋長186.0m、最大スパン97.0m、幅員記載。',
 '- [東京都公園協会・木場公園](https://www.tokyo-park.or.jp/park/kiba/) — 公園の南・中・北3地区と橋の連絡関係。',
 '- OSM raw snapshot (downloaded Phase 1), © OpenStreetMap contributors, ODbL 1.0: `data/raw/osm/layers/paths/footpaths.osm`, `bridges.osm`.']
(ROOT/'reports/phase2j/phase2j_validation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Phase 2J validation PASS; Phase 2C SHA-256',nav_sha,'screenshots',len(shots),'routes',round(route1,3),round(route2,3))
