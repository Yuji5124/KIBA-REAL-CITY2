# KIBA PARK REBUILD — Phase 2I 検証

## 結果

Phase 2I の独立したDEV接続候補を生成し、実ブラウザーでON/OFFと両方向の移動を確認した。OFFでは従来どおり16.609m地点でBLOCK。Phase 2H実験モードとPhase 2I候補を両方ONにした場合のみ、Run A→B、Run B→Aが各200ステップでPASSした。候補はデフォルトOFFで、Phase 2C本番ナビゲーションには反映していない。

## ギャップの発生原因

対象はOSM way `33976871`。raw OSM上のwayは3ノード・174.289mの連続した形状で、way自体の欠落ではない。Phase 2Aの`clipped_runs`が公園境界との交差で線分を分割し、公園ポリゴン内側だけを保持する。その結果、境界外区間を挟んでPhase 2CにRun AとRun Bが残り、自動接続されなかった。DEM/標高補間が変えるのはY（高さ）であり、XY方向の16.609m間隔は生成していない。よって原因は**公園境界クリップ**と判定した。

| 計測 | 値 | 根拠・扱い |
|---|---:|---|
| Run A終端 → Run B始端の水平距離 | 16.609m | Phase 2Hのクリップ済み座標 |
| 端点間3D距離 | 16.616m | Y差を含む |
| 高さ差（A→B） | -0.476m | いずれも推定橋面高 |
| 直線接続の勾配 | -2.866% | 推定端点間の平均 |
| Run A終端接線 | -92.645° | +X基準 |
| Run B始端接線 | -33.345° | +X基準 |
| 接線の向き差 | 59.300° | Phase 2Hサンプルの接線 |
| Phase 2F視覚補完 | 16.609m・幅4m | 直線の表示用、衝突なし |

## DEV接続候補

Phase 2Fの直線表示面とは独立したPhase 2I候補を追加した。4m幅（推定）、Run A/Bの推定標高、端点接線に沿う3mハンドルのXYベジェ曲線とスムースステップ高さを使用する。中心線は16.991m、181点、最大勾配は4.299%、Phase 2F直線中心線からの最大偏差は1.756m。表示面は180クワッド。候補の高さ、幅、曲線はすべて推定値で、実測橋面や構造的に安全な接続の証明ではない。

ブラウザーで確認した安全ゲート：

- DEV候補OFF：A→Bは「16.609mギャップ」でBLOCK。
- DEV候補ONかつPhase 2H実験モードON：A→BとB→Aが各200ステップでPASS。
- 候補の横方向外側、候補終端の先、未モデル化方向はBLOCK。
- 未モデル化延長100.555mは接続していない。ブラウザーの100.555m試験は実際の橋軸を示すものではなく、接続されないことを確認するための仮想安全プローブ。
- 通常モードではPhase 2C判定を使い、橋梁は通行不可。橋梁13 runの既存状態は8 review / 5 blocked / 0 walkableのまま。

Phase 2CナビJSONのSHA-256はPhase 2Hと同じ`2a127eff41dce83fb98b3fc725bcc130d060495f3b2c2ffcc27e65bca7578b55`。生成物検証では181点の有限座標、候補端点との一致、最大サンプル間隔0.1211m、スクリーンショット4枚（各1280×720）を確認した。

## ブラウザー描画負荷

| 視点 | Phase 2H基準 FPS / calls / tris / meshes | Phase 2I候補ON FPS / calls / tris / meshes |
|---|---:|---:|
| 上空 | 60.1 / 62 / 629,090 / 58 | 60.0 / 63 / 629,450 / 59 |
| 橋梁地上 | 53.2 / 50 / 554,052 / 58 | 60.1 / 51 / 554,412 / 59 |
| 側面 | 50.2 / 51 / 554,064 / 58 | 55.6 / 53 / 554,784 / 59 |
| ロボット | 49.0 / 49 / 630,604 / 58 | 54.2 / 49 / 630,604 / 59 |

候補面追加分は橋梁地上で+1 draw call、+360 triangles、+1 mesh（上空で+1 / +360 / +1）。FPSは端末負荷、カメラ、植生LOD、ブラウザー実行タイミングで変わるため、比較値は画面上で読んだ瞬時値であり、制御ベンチマークではない。

## 実ブラウザー画像

- [上空視点](../../screenshots/phase2i/phase2i_top.png)
- [橋梁地上視点](../../screenshots/phase2i/phase2i_bridge.png)
- [側面視点](../../screenshots/phase2i/phase2i_side.png)
- [ロボット視点](../../screenshots/phase2i/phase2i_robot.png)

## 未確定・残課題

実測の橋面高さ、正式な幅、支持構造、境界での橋の実際の連続性を示す測量点や設計図がない。よって成功した試験は候補面上の限定DEVシミュレーションに限る。物理的な通行安全性は未検証であり、Phase 2C本番ナビへの登録、通常モードでの橋梁通行、未モデル化延長の接続は行っていない。

## Windows PowerShell

クローンのルートで実行する。

```powershell
cd C:\Users\hp\Desktop\KIBA-REAL-CITY
python scripts\phase2i\build_phase2i.py
python scripts\phase2i\verify_phase2i.py
python scripts\phase2i\serve_phase2i.py
```

ブラウザーで `http://127.0.0.1:8782/web/phase2i/` を開く。生成し直すときは、実行中のサーバーをCtrl+Cで止めてからbuildを実行する。成果物は`build-phase2i`、計測レポートは`reports/phase2i`、ブラウザーPNGは`screenshots/phase2i`に分離している。
