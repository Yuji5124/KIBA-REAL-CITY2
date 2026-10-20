# CLAUDE.md — KIBA PARK REBUILD

## Project
木場公園全域の3DデジタルフィールドをBlender（MCP／ヘッドレスbpy）とThree.jsで制作する。

## Primary AI
Claude Codeのみを開発統括に使用する。

## Core Principles
1. 実際の地理データを優先する
2. 既存のKIBA-REAL-CITY（`Desktop\KIBA-REAL-CITY-main`）を破壊しない — 読み取り専用で参照する
3. Blender MCPを3D制作と確認に利用する（未接続の間はヘッドレスbpyで生成し、同じスクリプトを保存）
4. 反復作業はPythonスクリプトで再現可能にする
5. 地形・橋・樹木・建物を独立管理する
6. GLBは軽量化してHTMLで読み込む
7. iPhone・iPad・PCの性能を考慮する
8. 見た目の品質とゲームとしての視認性を両立する
9. ロボット戦闘用のコリジョンを別管理する
10. ARは通常ゲームから分離する

## Coordinate rules（docs/phase0/COORDINATE_SYSTEM.md）
- EPSG:6677、原点 E=-2302.317826321731 / N=-36106.717222697174、メートル、標高はT.P.
- Blender (x, y, z) = (東, 北, 標高)／Three.js (x, y, z) = (東, 標高, -北)
- 変換は必ず `scripts/kpr_coords.py` を使い、変更時は `python tests/test_coords.py` を実行

## Development Workflow
調査 → 設計 → 最小実装 → Blender確認 → HTML確認 → テスト → 改善 → 記録

## Safety
- 既存データの削除・上書き禁止
- ライセンス不明素材の採用禁止
- 未確認のAPIや機能を推測しない
- GitHub pushは許可を得る
- データ精度と推定値を区別する（オブジェクトに `is_estimate` を付ける）

## Completion Report
各Phase完了時に日本語で報告する：実装内容／生成ファイル／実行したテスト／実測した性能／未解決の問題／次のPhaseへの条件

## Priority
正確な地形 → 安定したHTML → 橋 → 樹木 → 画質 → ロボット戦闘 → AR

## Phase order（2026-10-17 承認）
0 調査・設計（完了）→ 1 全域地形・園路・HTML → 2 木場公園大橋・主要建物 → 3 樹木・植生 → 4 画質 → 5 ロボット戦闘 → 6 AR・最適化

## Blender MCP
- 接続完了と報告してよいのは、MCP経由でシーン操作が実際に成功した場合のみ
- 未接続の間は scripts/blender/ のバッチ（bpy）で生成し、同じスクリプトを後でMCP経由で再実行する
