# KIBA PARK REBUILD Phase 2J — 橋梁範囲調査

## 結論

The 250m minus 149.445m result is arithmetic, not one located missing segment. OSM has a three-arm bridge-tagged walkway junction: the 174.289m trunk and two distinct 76.9–78.1m branches. The Phase 2F main-way display also omits parts cut by the park boundary. North-to-south paths via either branch total about 251–252m, near the rounded 250m source value. This supports—but does not prove—a full route interpretation. The 186m engineering length remains definitionally unreconciled. No added bridge mesh is justified.

資料値の250mと186mには64mの差がある。都の公園管理計画/JCIアーカイブは3地区を結ぶ橋の全長を250mと記し、1995年のPC建協技術資料は2径間連続PC斜張橋の橋長を186.0m、最大スパン97.0m、標準幅10.8–25.8m、分離部8.228mと記す。JCIの最大支間96.95mと主塔高60mはそれぞれ公開資料の丸め違いと整合する。測定端点・取付部の扱いは資料上で確認できず、250mがアクセス歩道込み、186mが構造物長という説明は推定としてのみ扱う。

## OSMトポロジーと距離

| 要素 | OSM/測定値 | 位置・読み方 |
|---|---:|---|
| 主線 way 33976871 | 174.289m | 3ノード、bridge=yes / footway。共有節点から北側端へ |
| 南側分岐 way 598428792 | 77.975m | 主線の共有節点からnode 6400941151へ |
| 南側分岐 way 683394375 | 76.808m | 主線の共有節点からnode 6400941152へ |
| 北端→南側端の経路 | 252.264m / 251.098m | 各分岐を別々に通る2経路。250mに近いが現況測量値ではない |
| OSM橋梁外形 way 745579214 | 248.80×59.38m | 47ノードの閉ループ。外形範囲であり床版線ではない |

3つのbridge=yes歩道はnode `6980957124`で分岐し、OSM橋梁外形の南北範囲は約249m。これは橋が単一直線ではなく、北側の主線と南側二方向の枝を持つ可能性を示す。北端から各南側端へのOSM経路長は約251.1mと252.3mで、公開250m値と近い。OSMは編集地図であり、測量・竣工図ではないため、構造端点を確定しない。

## 250m差の分解

Phase 2Fの149.445mはway 33976871の公園内クリップ済み132.836mと16.609mの表示専用ギャップ補間の合計。raw way自体は174.289mなので、クリップ表示から外れた同一way区間は約24.844m。さらに独立した二本の南側枝が約76.808mと77.975mある。従って`250 - 149.445 = 100.555m`は算術残差であり、単一の未制作区間の長さ・位置ではない。枝を各々一つずつ通る全ルートは251.098m/252.264mだが、公表値との1.098m/2.264m差は丸め・端点定義・地図線形の差かもしれず、根拠なく補正しない。

Phase 2Iで特定した16.609mギャップは公園ポリゴンの境界クリップによる。これは250m全体の差や分岐形状とは別の問題である。Phase 2Cは境界外線分を除き、二本のRunを自動接続していない。

## G6.2・主塔・支間の照合

G6.2は主塔2、横梁1、ケーブル24の27メッシュで、橋面メッシュはない。モデルのZ方向外形は188.039m、主塔の高さは60m。Z範囲は支線ケーブルを含むメッシュ外形であり、デッキの橋長とみなせない。モデルは測量基準点なしの恒等配置仮説で、軸メタデータも頂点配置と矛盾する。
ローカル座標でOSM主線と主塔中心軸の最近距離は約0.356mで、平面上の横位置は近い。一方、主塔位置はOSM共有節点から主線station約38.674m、北端まで約135.616mにあり、96.95m最大支間を照合できない。デッキ両端と支承位置がモデルにないため、スパン割り・橋の北端・分岐側接合点は未確定。

## 根拠区分

| 項目 | 値/観察 | 分類 |
|---|---|---|
| 全長 | 250m | 公開資料値・測定端点未定義 |
| 橋長 | 186.0m | 公開技術資料値・250mとの範囲定義未照合 |
| 最大支間 | 96.95m / 97.0m | 公開資料値（精密値/丸め） |
| 主塔高 | 60m | 公開資料値。G6.2形状にも60m高があるが測量照合なし |
| way 33976871 | 174.289m | OSMからEPSG:6677に投影した線形長 |
| Phase 2F表示候補 | 149.445m | クリップ済み主線＋視覚ギャップ補完。構造長ではない |
| Phase 2Fの4m幅 | 4m | 推定値。技術資料の幅と適用範囲が不整合 |
| G6.2外形 | 188.039m | モデルの頂点外形。橋長ではない |
| 南側二本の枝と外形 | 76.808m、77.975m、閉外形約59×249m | OSMタグ/ジオメトリ。竣工測量ではない |
| 250m−149.445m | 100.555m | 算術残差。位置未確定・単一区間ではない |

## 実ブラウザーと描画負荷

Phase 2J専用URLで上空・橋梁地上・側面・ロボット視点を確認し、OSM主線・分岐・外形を標高なしの点線オーバーレイで表示した。通常モードに戻して終了し、Phase 2Cの橋梁は通行不可、Phase 2I DEV接続候補はOFF。24m公園園路テストは326 swept probes、要確認通過0、階段・35%超・ギャップ・境界BLOCKでPASS。ロボット視点だけPhase 2H実験レイヤーを使った撮影後、通常モードへ復帰した。

| 視点 | Phase 2H基準 FPS / draw / tris / meshes | Phase 2J観測 FPS / draw / tris / meshes |
|---|---:|---:|
| 上空 | 60.1 / 62 / 629,090 / 58 | 55.3 / 62 / 627,814 / 56 |
| 橋梁地上 | 53.2 / 50 / 554,052 / 58 | 60.1 / 50 / 552,776 / 56 |
| 側面 | 50.2 / 51 / 554,064 / 58 | 50.2 / 44 / 552,264 / 56 |
| ロボット | 49.0 / 49 / 630,604 / 58 | 60.1 / 53 / 630,604 / 58 |

画面HUDの瞬間値であり、視錐台、植生LOD、操作・ブラウザー負荷で変動する。ロボット視点はPhase 2Hの推定Run上から取得し、通常モードの歩行可能性を示していない。

### 保存画像と比較

- [上空](../../screenshots/phase2j/phase2j_top.png)
- [橋梁地上](../../screenshots/phase2j/phase2j_bridge.png)
- [側面](../../screenshots/phase2j/phase2j_side.png)
- [ロボット](../../screenshots/phase2j/phase2j_robot.png)

Phase 2I側はDEV接続候補ONで保存された既存画像、Phase 2J側はDEV接続候補OFF・OSM平面トレースON。完全な同一レイヤー条件の性能比較ではなく、表示レイヤーの差を確認する画像。
| 視点 | 比較画像 |
|---|---|
| 上空 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_top.png) |
| 橋梁地上 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_bridge.png) |
| 側面 | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_side.png) |
| ロボット | [Phase 2I / Phase 2J](../../screenshots/phase2j/phase2j_compare_robot.png) |

## 次に必要な根拠

1. 250m記載の測定端点と取付部を示す整備計画図または竣工一般図。186mの構造端点、両径間長、支間割りを照合できる断面・縦断図。
2. EPSG:6677測量基準点を持つ竣工座標またはGNSS/トータルステーション点（塔中心、桁端、支承、北側端、南側二分岐の接合部）。
3. 二本の南側枝と北側取付部の橋面縦断・幅員・高さを示す平面/縦断/横断図。PC技術資料の10.8–25.8m、8.228mの幅がどの部分に対応するかの説明。
4. クリップ境界付近と南側端部の現況航空写真・LiDARまたは現地測量。OSMは形状候補の追跡には有用だが高さや構造端点の根拠にはならない。

根拠不足のためPhase 2Jでは橋梁メッシュを追加していない。Phase 1〜2I、rawデータ、Phase 2Cナビ、元G6.2、KIBA-REAL-CITY-mainには書き込みを行っていない。

## 再生成・検証・起動（Windows PowerShell）

Phase 2Iの保存済みビルド（`build-phase2i`）があるクローンのルートで実行する。Phase 2Iの再生成は不要。

```powershell
cd C:\Users\hp\Desktop\KIBA-REAL-CITY
python scripts\phase2j\build_phase2j.py
python scripts\phase2j\verify_phase2j.py
python scripts\phase2j\serve_phase2j.py
```

`http://127.0.0.1:8783/web/phase2j/` を開く。OSMオーバーレイは「OSM線形・橋梁外形を表示」で切替できる。高さ・デッキ・衝突判定のレイヤーではない。

## 参照

- [東京都建設局・木場公園マネジメントプラン](https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/070328kbetsumpkiba) — 3ゾーンを連絡する全長250m、主塔高60m。
- [日本コンクリート工学会・木場公園大橋](https://www.jci-net.or.jp/photo_60/archive/detail_db.php?id=168&page=6) — 250m、最大支間96.95m、2径間連続PC斜張橋。
- [プレストレスト・コンクリート建設業協会・1995技術資料PDF](https://jpci.or.jp/data/pc-seminar/text/023_pc-seminar-text_199502.pdf) — 木場公園橋、橋長186.0m、最大スパン97.0m、幅員記載。
- [東京都公園協会・木場公園](https://www.tokyo-park.or.jp/park/kiba/) — 公園の南・中・北3地区と橋の連絡関係。
- OSM raw snapshot (downloaded Phase 1), © OpenStreetMap contributors, ODbL 1.0: `data/raw/osm/layers/paths/footpaths.osm`, `bridges.osm`.
