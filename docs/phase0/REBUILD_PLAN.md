# REBUILD_PLAN — 制作基盤の設計とPhase 1への移行条件（Phase 0）

作成：2026-10-17。関連：DATA_INVENTORY / DATA_SOURCES / COORDINATE_SYSTEM / TILE_PLAN / ASSET_PLAN

---

## 1. 作業環境の調査結果（実測）

| 項目 | 結果 |
|---|---|
| PC | Windows（x64）、Claudeデスクトップアプリ 2.42304.0、Node 24.21 |
| PCの既存環境（README記載） | Blender 4.4（`C:\Program Files\Blender Foundation\Blender 4.4\blender.exe`）、Python 3.12系の仮想環境（venv / venv312）|
| **Blender MCP（このセッション）** | **未接続**。ツール一覧に存在せず、デスクトップアプリ側のローカルMCPサーバーも0件 |
| デスクトップの「Blender MCP」フォルダ | Tayoバスの作業ファイルのみ。MCPサーバー本体ではない |
| PCでのコマンド実行 | **不可**（このセッションはファイルの読み書きのみ。シェルは使えない） |
| クラウド作業環境のBlender | **Blender 5.2.2（bpyモジュール）をインストールし、メッシュ生成→GLB出力まで動作確認済み**。DracoとMeshoptはこのbpyに含まれない → 圧縮はglTF-Transformで行う |
| クラウドからのGISデータ取得 | **不可**（OSM・国土地理院・PLATEAUとも接続拒否）。npm・PyPIは可 |
| Rapier | `@dimforge/rapier3d-compat` 0.21.0 をNode上で動作確認。地形heightfield＋カプセル＋キャラクターコントローラーで、地面に接地（grounded=true、高さ誤差0.05m） |

### Blender MCPの扱い
「利用できない機能は存在すると仮定しない」に従い、MCPのツール名・機能一覧は**空（確認できず）**として記録します。接続する方法は次のどちらかです。

1. **Claudeデスクトップアプリ**にBlender MCP（PyPI `blender-mcp` 2.0.0、MITライセンス）をローカルMCPサーバーとして登録し、Blender側のアドオンを起動する → このセッションから見えるようになる可能性あり（接続後に再確認が必要）
2. Windows上の**Claude Code**（ターミナル版）でBlender MCPを設定し、そちらで作業する

どちらも難しい場合の代替：**生成はクラウドのbpy（Python）、目視確認はPCのBlender 4.4でGLBを開く**。すべての処理はPythonスクリプトとして保存するので、MCPがつながった後も同じスクリプトをMCP経由で実行できます。
※ Blender 5.2で保存した.blendは4.4では正しく開けない可能性があるため、**クラウドからは.blendを渡さず、GLBとスクリプトだけ**を渡します。

---

## 2. 利用するライブラリ・リポジトリ（ライセンス確認）

| 名称 | 版 | ライセンス | 用途 | 互換性・確認 |
|---|---|---|---|---|
| three.js | 0.186.1 | MIT | 描画 | 既存プロジェクトと同じ版 |
| Vite / TypeScript | 8.3.4 / 5.9.3 | MIT / Apache-2.0 | ビルド | 既存と同じ |
| @dimforge/rapier3d-compat | 0.21.0 | Apache-2.0 | 物理・衝突 | **Nodeで動作確認済み**。ブラウザ（iOS Safari）での確認はPhase 5 |
| three-mesh-bvh | 0.9.16 | MIT | 地面判定・カメラのめり込み防止のレイキャスト高速化 | Phase 1で導入 |
| @gltf-transform/core・cli | 4.5.1 | MIT | GLBの圧縮（meshopt）、テクスチャKTX2化 | KTX2化にはKTX-Software（toktx）が別途必要。要確認 |
| meshoptimizer | 1.3.0 | MIT | 頂点圧縮・簡略化 | three.jsのMeshoptDecoderで読込可 |
| postprocessing | 6.39.5 | Zlib | ポストエフェクト（Phase 4で最小限） | 重い効果は使わない |
| @google/model-viewer | 4.4.0 | Apache-2.0 | iPhone向けAR代替（Quick Look） | Phase 6で評価 |
| mind-ar | 1.2.5 | MIT | 画像マーカーAR（代替案） | 2024-01以降更新なし。保守リスクあり |
| blender-mcp（PyPI） | 2.0.0 | MIT | Blender制御 | **未接続** |
| bpy（PyPI） | 5.2.2 | GPL（Blender本体） | クラウドでのヘッドレス生成 | 動作確認済み。ゲームに組み込まないのでGPLの影響は出力物に及ばない［一般的な解釈、法的助言ではない］ |
| BlenderGIS | — | GPL-3.0 | 参考のみ（コードは取り込まない） | 既存プロジェクトの調査結果を引き継ぎ |
| MOSAIQ（OSM→Blender） | — | Apache-2.0 | 参考のみ | 同上 |
| pyproj / shapely / numpy / Pillow | — | MIT / BSD | GIS処理 | requirements.txtに既存 |
| rasterio / geopandas | — | BSD | 指示書にあるが**必須ではない** | DEMはPNGタイルなのでPillowで足りる。Windowsでの導入の手間を避けるため保留 |

npmとPyPIのライセンス欄で確認（2026-10-17）。GitHubのページは今回のセッションでは開けなかったため、npm/PyPIの登録情報で代替しています。

---

## 3. プロジェクト構成（新規：`C:\Users\hp\Desktop\KIBA-REAL-CITY\`）

既存の `KIBA-REAL-CITY-main` には**一切書き込まず**、空だった `KIBA-REAL-CITY` を新しいプロジェクトの置き場所にします。

```
KIBA-REAL-CITY/                  ← KIBA PARK REBUILD
├─ CLAUDE.md                     開発ルール
├─ docs/phase0/                  本調査の成果物（6点）
├─ config/park.json              原点・範囲・タイル設定（Phase 1）
├─ scripts/
│   ├─ kpr_coords.py             座標系の唯一の定義
│   ├─ phase0_tile_plan.py       タイル分割の検証
│   ├─ fetch/                    PC側で実行するデータ取得（OSM・DEM・航空写真）
│   ├─ gis/                      DEM→格子、OSM→園路・広場・水域
│   └─ blender/                  Blender内で実行する生成・出力（MCP／ヘッドレス両対応）
├─ tests/                        座標・タイル境界・GLB検証
├─ data/
│   ├─ legacy_ref → 既存-mainを読むだけ（パスを設定で指定、コピーしない）
│   ├─ raw/                      新規取得データ（Git管理外）
│   └─ processed/
├─ assets/                       生成GLB（tiles/, bridge/, trees/, robots/）
└─ web/                          Three.jsアプリ（Vite+TS）
```

---

## 4. Three.jsの実装構成

```
web/src/
├─ core/       Renderer（画質プリセット：PC／モバイル）、ループ、FPS・メモリ計測
├─ world/
│   ├─ TileStreamer      カメラ位置から必要なタイルとLODを決め、GLBを読み込み・破棄
│   ├─ Terrain           高さの問い合わせ（heightAt(x,z)）、境界の継ぎ目処理
│   ├─ Vegetation        InstancedMesh、距離でLOD切替、近距離だけ草
│   ├─ Water             水面（軽量シェーダー）
│   └─ Landmarks         橋・建物（独立GLB）
├─ physics/    Rapier（heightfieldはタイル単位、橋・建物は簡易形状）
├─ game/       ロボット、敵AI、戦闘、勝敗（Phase 5）
├─ input/      キーボード・マウス・タッチ（既存のWALK/FLY操作を移植）
├─ camera/     自由移動カメラ（Phase 1）、追従カメラ（Phase 5）、地面へのめり込み防止
├─ xr/         AR（Phase 6、通常版とは別の入口で読み込む）
└─ debug/      ?debug=1 の計測パネル（既存の仕組みを踏襲）
```

既存の `phase4-web` から流用するもの：WALK/FLY操作とタッチスティック、デバッグ表示、WebGLコンテキスト喪失時の復帰、資産のハッシュ照合。**コピーして新しいフォルダで改修**し、元のファイルは変更しません。

---

## 5. Phase 1 の実装案

| 手順 | 内容 | 実行場所 | 成果物 |
|---|---|---|---|
| 1-1 | データ取得：OSM（公園＋50m余白、約0.5×1.1km）、DEM1A z17の15枚（不足6枚）、DEM5A補完、航空写真（Phase 3用） | **PC**（スクリプトを渡す） | data/raw/ |
| 1-2 | DEM→1m格子のモザイク→欠損補完→2m/5m/10m格子 | クラウド | processed/dem_*.npy |
| 1-3 | OSM→園路（種別ごとの幅は推定と明記）、広場、水域、植栽区域。公式施設名で照合 | クラウド | processed/paths.geojson ほか |
| 1-4 | Blenderで100mタイル×55枚を生成し、園路・広場・水面を地形に沿わせる。タイルごとにGLB出力 | クラウド（bpy）→ MCP接続後はBlender | assets/tiles/*.glb |
| 1-5 | meshopt圧縮、タイル目録（manifest.json） | クラウド | |
| 1-6 | Three.jsビューア：タイル読み込み、自由移動カメラ、地面めり込み防止、スマホ操作 | クラウドで開発→PCで確認 | web/ |
| 1-7 | 検証：座標テスト、タイル境界の高さ差、GLB再読み込み、ヘッドレスブラウザでの表示とFPS | クラウド | tests/、reports/ |
| 1-8 | Blenderでの目視確認、iPhone/iPadでの表示確認 | PC・実機 | スクリーンショット |

### Phase 1 に進むための条件
- [x] 座標系・原点・タイル設計の確定（本書）
- [x] 公園全域の範囲の確定（OSM relation/14273608）
- [ ] **公園全域のOSM・DEMの取得（PCでスクリプト実行が必要）**
- [ ] Blender MCPの接続方法の決定（または「bpyで生成＋PCのBlenderで確認」で進める合意）
- [ ] 旧v07ファイルの所在（比較に使う場合のみ。無くても進められる）

---

## 6. 以降のPhaseの要点（調査で分かったこと）

| Phase | 要点 |
|---|---|
| 2 橋・建物 | **Phase 3の前に実施することが承認済み（2026-10-17）** |
| 3 植生 | OSMの樹木点は33本のみ。全域の密度は航空写真から推定（推定値として記録）。高木10・低木5種 |
| 4 画質 | 影はカメラ周辺だけの1枚のシャドウマップ（モバイルでは解像度を下げる）。木漏れ日は影ではなく地面へのライトクッキー（投影テクスチャ）で軽く表現。VISUAL EFFECT LIBRARY（GitHub Yuji5124/visual-effect-library、MIT）に候補あり → PHASE1_READINESS.md §5 |
| 5 戦闘 | Rapier 0.21を採用候補。動作確認済み。戦闘エリアは多目的広場・イベント広場を候補に |
| 6 AR | 下記 |

### AR（Phase 6）の事前調査
- **iPhone/iPadのSafariはWebXR（immersive-ar）に非対応**（caniuse：iOS Safari 26.6・27.0〜27.2とも非対応、2026年6月の業界記事でも「2026年もiPhoneのSafariは手持ちARを公開していない」）
- Android版ChromeはWebXRのARに対応（hit-testで床にロボットを置く方式が可能）
- iPhone向けの代替：①通常の3Dゲーム（主）②AR Quick Look（USDZ）でロボットや公園のミニチュアを床に置く（ゲーム操作は不可）③App Clip経由のWebXR（外部サービス依存）
- 8th Wallは2026年3月にホスティングを終了し、エンジンをMITで公開（SLAMは含まれない）→ 採用は推奨しない
- 現実の公園との位置合わせ：GPSの誤差（数m〜10m）では足りないため、「現地の目印（橋の主塔など）を画面で合わせる手動調整」が現実的

---

## 7. 不足データとリスク

| # | 内容 | 影響 | 対策 |
|---|---|---|---|
| R1 | Blender MCPが未接続 | 「MCPで生成・確認」の指示どおりに進められない | bpyで生成し、スクリプトを保存。MCP接続後に同じスクリプトで再確認 |
| R2 | クラウドからGISデータを取得できない | Phase 1の開始条件 | PCで取得スクリプトを実行してもらう（1回、数分） |
| R3 | PCでコマンドを実行できない | PCでのビルド・実機確認は手作業 | 手順書とバッチファイルを用意 |
| R4 | v04〜v07が手元にない | 既存ビューアが動かない。G6.2の橋床が無い | 新しいビューアで代替。比較はv03とG6.2で行う |
| R5 | 園路の幅がOSMにない（236本中0本） | 園路の見た目の精度 | 種別ごとの推定幅（推定と明記）＋航空写真で主要園路だけ補正 |
| R6 | DEM1Aの欠損（水面・建物下で最大15%） | 地形の穴 | DEM5Aで補完、水面は平面化 |
| R7 | 樹種・樹高のデータがない | 森の再現性 | 航空写真からの密度推定。樹種は候補として扱う |
| R8 | 公式園内マップはトレースできない可能性 | 広場の形 | OSMの形を使い、公式マップは名称・位置の照合だけ |
| R9 | ODbL／PLATEAUの再配布条件 | 公開時 | **ローカル利用・非公開**を前提。公開する前に再確認 |
| R10 | iPhoneはWebXR非対応 | ARの範囲 | 通常版を主にし、Quick Lookを代替に |
| R11 | モバイル性能（iPad Air第3世代など） | 30fps目標 | 実機計測するまで目標値は「仮」。画質プリセットを用意 |
| R12 | 参考の森の画像・NEXUS・VFX LIBRARY | Phase 3・4・5の基準 | **解決**：画像は受領、NEXUS・VFX LIBRARYはGitHubで確認（PHASE1_READINESS.md §5） |
| R13 | Blender MCPがClaude側に未登録（Codexにのみ登録） | MCPでの確認ができない | PHASE1_READINESS.md §2 の手順A／B |
