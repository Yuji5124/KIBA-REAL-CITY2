# KIBA PARK REBUILD Phase 2G 検証レポート

## 判定
PASS — Phase 2G生成物、4視点の実ブラウザー表示、移動制限を確認。Blender MCPツールは利用可能一覧に無かったため、Three.jsの別メッシュを使用。

## 座標・メッシュ整合性
- 候補面320 quad（OSM way 33976871の319面、境界ギャップ視覚候補1面）。頂点1,280件は有限値で、EPSG:6677ローカル範囲内。
- 橋下面・縁部・欄干を独立3メッシュ群として追加。OSMマッピング面だけに適用し、ギャップへは延長していない。衝突なし。
- G6.2は27メッシュ（主塔2、横梁1、ケーブル24）、356 triangles。橋面なし。G6.2本体は変更していない。
- 橋面中心線はモデル由来の主塔中心線から平面上で最短約0.34m。上空・地上・側面でケーブルとの配置を確認したが、これはローカルモデル座標の比較であり測量精度ではない。GLBのZ-up記述と頂点のY-up解釈は未解決。
- OSM way全体174.289m、表示候補149.445m。公表全長250mとの差100.555mは未収録。

## 移動判定
way 777288664で24.0m、326 swept probes、PASS。要確認区間通過0。階段・35%超勾配・ギャップ・境界外はすべてBLOCK。
Phase 2Cナビデータは元と同一SHA-256: 2a127eff41dce83fb98b3fc725bcc130d060495f3b2c2ffcc27e65bca7578b55。橋梁13 runは要確認8 run/760 segment、通行不可5 run/146 segment、通行可能0。Phase 2Gではナビ・衝突判定を変更していない。

## Phase 2Fとの実ブラウザー比較
同じブラウザーの視点プリセットでHUD値を記録。FPSはすべて約60.1。三角数やdraw callsはフラスタム、植生LODにより変わる観測値。

| 視点 | Phase | FPS | Draw calls | Triangles | Scene meshes |
|---|---|---:|---:|---:|---:|
| 上空 | 2F | 60.1 | 55 | 600,380 | 53 |
| 上空 | 2G | 60.1 | 58 | 627,814 | 56 |
| 橋梁地上 | 2F | 60.1 | 43 | 525,342 | 53 |
| 橋梁地上 | 2G | 60.1 | 46 | 552,776 | 56 |
| 側面 | 2F | 60.1 | 37 | 524,830 | 53 |
| 側面 | 2G | 60.1 | 40 | 552,264 | 56 |
| ロボット | 2F | 60.1 | 21 | 559,052 | 53 |
| ロボット | 2G | 60.1 | 19 | 541,188 | 56 |

## 完了部分・推定部分・未解決部分
完了: 別レイヤー表示、320面の座標検査、下面・縁部・欄干候補、4視点の実ブラウザー確認、移動テスト、Phase 2C保持検証、4枚のPNG保存。
推定: 4.0m幅、橋面標高1.568–4.940m、下面厚0.32m、縁部高0.18m、欄干高1.05m、G6.2恒等変換配置。測量・構造図による確定値ではない。
未解決: 全長に対する未収録100.555m、G6.2の軸・原点・縮尺の測量登録、16.609m境界ギャップ、園路との高さ連続性、継手・接合部・支承。橋面は視覚候補のままでロボット通行不可。

## スクリーンショット
- screenshots/phase2g/phase2g_top.png
- screenshots/phase2g/phase2g_bridge.png
- screenshots/phase2g/phase2g_side.png
- screenshots/phase2g/phase2g_robot.png

## 参照資料
- [東京都公園協会・木場公園](https://www.tokyo-park.or.jp/park/kiba/index.html) — 全長250m、主塔高60m。
- [Japan Concrete Institute・木場公園大橋](https://www.jci-net.or.jp/photo_60/archive/detail_db.php?id=168&page=6) — 250m、最大支間96.95m、2径間連続PC斜張橋。
- [木場公園大橋の写真（CC BY-SA 4.0）](https://commons.wikimedia.org/wiki/File:Kiba_Park_bridge_view.jpg) — 外観参照。寸法根拠ではない。

## Windows PowerShell
クローンのルートから:
    python scripts\phase2g\build_phase2g.py
    python scripts\phase2g\verify_phase2g.py
    python scripts\phase2g\serve_phase2g.py
ブラウザー: http://127.0.0.1:8780/web/phase2g/
