# DATA_INVENTORY — 既存KIBA-REAL-CITYの資産一覧（Phase 0）

調査日：2026-10-17（JST）／調査方法：デスクトップアプリ経由の読み取り専用（一覧取得とコピーのみ）。**既存ファイルは1つも変更・移動・削除していません。**

## 0. 調査対象フォルダ

| パス | 状態 | 備考 |
|---|---|---|
| `C:\Users\hp\Desktop\KIBA-REAL-CITY` | **空フォルダ** | 今回選択されたフォルダ。新規プロジェクト「KIBA PARK REBUILD」の置き場所として使用 |
| `C:\Users\hp\Desktop\KIBA-REAL-CITY-main` | 既存プロジェクト本体（842ファイル／約201MB、うちnode_modules 731件） | GitHubのZIP展開と思われる名称。**参照専用（読み取りのみ）** |
| `C:\Users\hp\Desktop\Blender MCP` | Tayoバス制作の作業フォルダ（.blend、.py、参考画像100枚） | **Blender MCPサーバー本体ではない**。本プロジェクトとは無関係 |
| `NEXUS` / `VISUAL EFFECT LIBRARY` | 追補で発見 | デスクトップのWebアプリショートカット。実体はGitHub Yuji5124/nexus・visual-effect-library（PHASE1_READINESS.md §5） |

全ファイル一覧（node_modules除く111件）：`data/phase0/existing_file_inventory.csv`

## 1. 3Dモデル（GLB / BLEND）— `output/`

| ファイル | サイズ | 内容（実測） |
|---|---|---|
| KIBA_REAL_CITY_v01.blend / .glb | 2.0MB / 0.38MB | PLATEAU LOD1建物233棟（500m四方） |
| KIBA_REAL_CITY_v02.blend / .glb | 3.7MB / 0.70MB | +OSM道路236本・公園境界 |
| KIBA_REAL_CITY_v03.blend / .glb | 4.6MB / 0.92MB | +樹木点33・緑地17・水域14・橋2（平坦） |
| KIBA_REAL_CITY_v03_GSIterrain.blend / .glb | 5.7MB / 1.5MB | 国土地理院DEMの5m格子地形（101×101）にOSM面をドレープ |
| KIBA_REAL_CITY_v03_GSIterrain_clean.blend / .glb | 5.8MB / 2.0MB | 上記の整理版 |
| KIBA_REAL_CITY_v03_GSIterrain_polished.blend / .glb | 8.4MB / 5.9MB | 537ノード・537メッシュ・10マテリアル・**125,323三角形**・テクスチャなし。範囲 X,Z ±250m、高さ −1.67〜60.98m |
| **Kiba_Park_Ohashi_G6.2_visual_details.glb** | 40KB | 27メッシュ／356三角形。主塔2・横梁1・ケーブル24本。全ノード`visual_only:true`, `walk_collision:false` |

### 重要な欠落
- `phase4-web`（Three.jsビューア）は **`KIBA_REAL_CITY_v07.glb` と `geo_reference_v07.json`** をSHA-256固定で要求しますが、**このフォルダには存在しません**（v04〜v07はREADME記載のみ）。`.gitignore`で除外された生成物で、ZIPに含まれなかったと推定されます。
- そのため **既存ビューアはこのコピーでは起動できません**。v07の所在（別PC・別フォルダ）を確認する必要があります。
- G6.2橋ディテールは存在しますが、組み合わせる橋床（v07の橋床メッシュ）が欠落しています。v03系には OSM由来の橋床 `bridge_way_745579214` があります。

## 2. GISソースデータ — `data/`

| ファイル | 内容 | 状態 |
|---|---|---|
| raw/53394604_bldg_6697_op.gml (34MB) + .zip | PLATEAU江東区2023 建物LOD1 | 実測データ |
| raw/53394614_bldg_6697_op.gml (36MB) + .zip | 同上（北側メッシュ、現代美術館を含む） | 実測データ |
| raw/kiba_osm_phase2a.osm (1.1MB) | OSM API抽出（bbox 139.8050–139.8108E, 35.6722–35.6769N） | 公園リレーションの外周3wayは**完全に含む**が、それ以外の地物は500m四方のみ |
| raw/gsi_dem_tiles/ | DEM1A z17 3×3枚、DEM5A z15 2枚、DEM10B z14 2枚 | 公園北側（y=51613, 51614）の6枚が**不足** |
| processed/buildings.json | 建物233棟の加工済みフットプリント | |
| processed/phase2a_features.json / phase2b_features.json | 道路・緑地・水域・橋の加工済み地物 | |
| processed/gsi_dem_terrain.json | 5m格子の地形（10,201頂点） | 500m四方のみ |

## 3. スクリプト — `scripts/`（47件）

段階ごとに「download → convert → build（Blenderをヘッドレス実行）→ validate → render」の構成。上書き防止とSHA-256照合が全段に入っており、品質は高いです。再利用候補：

- `common.py`（設定・原点・JSON出力）、`download_gsi_dem.py`（DEMデコード、DEM1A→5A→5B→5C→10Bのフォールバック）
- `convert_phase2a_osm.py` / `convert_phase2b_osm.py`（OSM→EPSG:6677ローカル座標、出典メタデータ付与）
- `blender_gsi_terrain.py`（格子メッシュ化とドレープ）
- `validate_*.py`（Blender再読込によるGLB検証）

## 4. Webビューア — `phase4-web/`

| 項目 | 内容 |
|---|---|
| 構成 | Vite 8.3.4 + TypeScript 5.9.3 + three 0.186.1 |
| 機能 | WALK/FLY、建物AABB衝突、タッチ用仮想スティック、`?debug=1`でFPS・ドローコール表示、WebGLコンテキスト喪失時の復帰処理 |
| 資産読込 | Viteプラグインが`../output`のGLBをハッシュ照合して配信 |
| node_modules | Windows用バイナリでインストール済み。`@dimforge/rapier3d-compat 0.12.0` は `@types/three` の依存として入っているだけで、**アプリ本体では未使用** |
| 座標の扱い | 「X=東、Y=上、Z=−北」。GLBのジオメトリは変換していない |

## 5. 画像・レポート — `reports/`

プレビューPNG 4枚、generation_report（建物233棟の高さ・出典）、phase2a_validation（全項目PASS）。

## 6. 再構築で使えるもの／使えないもの

| 区分 | 判断 |
|---|---|
| **そのまま流用** | 共通原点（EPSG:6677）、PLATEAU GML、OSM公園境界、DEMデコード処理、出典メタデータの書式、上書き防止の方針 |
| **比較資料として利用** | v03_GSIterrain_polished.glb（地形・面）、G6.2橋GLB、プレビュー画像 |
| **範囲が足りない** | OSM地物・DEM・地形は500m四方のみ。**公園面積の54.5%しか入っていない**（全238,552m²中130,108m²） |
| **所在不明** | v04〜v07のGLB/BLEND/geo_reference、phase3d用のOSM抽出、NEXUS、VISUAL EFFECT LIBRARY、Phase 3の参考森林画像（今回は添付なし） |

## 7. 追補（2026-10-17）

- v07 GLB／geo_reference_v07：PC内・GitHubとも**見つからず**。不足素材として確定
- `Documents\Codex\KIBA-G6.2-bridge-20261017\`：G6.2の作業用.blendとreview.mdを確認
- 範囲の比較図：`docs/phase0/coverage_map.png`
