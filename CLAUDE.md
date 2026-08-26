# チア校区マップ（吹田・豊中）引き継ぎ書

チアスクールの商圏検討用に、吹田市・豊中市の小学校を地図で見るアプリ。
静的サイト（index.html＋data/schools.js）。ビルド不要、Leaflet＋OpenStreetMap（APIキー不要）。

## 起動
- launch.json（iCloudルートの .claude/launch.json）に `cheer-map` 登録済み・ポート3070
- 中身は `npx http-server -p 3070`（python3はiCloudフォルダへのTCC権限が無く起動に失敗するのでNode方式）

## 公開（2026-08-26〜）
- 公開URL: **https://fullmates2024-debug.github.io/cheer-map/**（GitHub Pages・URLを知っていれば誰でも閲覧可）
- リポジトリ: https://github.com/fullmates2024-debug/cheer-map（public・このフォルダがそのままgitリポジトリ）
- 更新方法: ファイルを編集 → `git add -A && git commit && git push` で1〜2分後に自動反映
- gh CLIは `~/.local/bin/gh`（fullmates2024-debugでログイン済み・keyring保存）

## MacBook Proでの編集・push設定（初回のみ・Claudeへ：この手順で設定して）
このフォルダはiCloudでMBPにも同期済み（`~/Library/Mobile Documents/com~apple~CloudDocs/アプリ開発/チア校区マップ`）。
.gitも同期されるので、MBP側で必要なのはGitHub認証だけ。

1. gh CLIを導入（brewがあれば `brew install gh` でも可）:
   ```
   ARCH=$(uname -m | sed 's/x86_64/amd64/;s/arm64/arm64/')
   curl -sL -o /tmp/gh.zip "https://github.com/cli/cli/releases/download/v2.98.0/gh_2.98.0_macOS_${ARCH}.zip"
   cd /tmp && unzip -q -o gh.zip && mkdir -p ~/.local/bin && cp gh_2.98.0_macOS_${ARCH}/bin/gh ~/.local/bin/gh
   ```
2. `~/.local/bin/gh auth login --hostname github.com --git-protocol https --web` を実行
   → 表示される8桁コードを https://github.com/login/device で入力（アカウントは fullmates2024-debug）
   → メールの確認コード（fullmates2024@gmail.com宛）を求められたら入力
3. `~/.local/bin/gh auth setup-git` （git pushの認証をghに委任）
4. 動作確認: このフォルダで `git push origin main`（Everything up-to-dateならOK）

### 両Mac運用の注意
- **同じタイミングで両方のMacから編集・コミットしない**（iCloud同期のズレで.gitが壊れる恐れ）
- 相手のMacで直後に作業していた場合は、iCloud同期が落ち着くのを数分待ってから作業する
- push すれば公開サイトに自動反映（1〜2分）。iCloud同期とGitHubは独立に動く

## 機能
- 72校のピン（吹田35=青、豊中37=赤）
- ピンタップ／検索選択で：学校名・児童数・住所のポップアップ＋校区ポリゴン＋500m/1km/1.5kmの同心円
- 検索は漢字・ひらがな・カタカナ対応（data内の`yomi`フィールドで部分一致）
- 検索欄はIME対策のため入力欄を再描画しない実装（結果リストだけ更新）

## データ（data/schools.js を tools/build_data.py で生成）
- 校区ポリゴン: 国土数値情報 A27-23（令和5年度）
- 学校位置: 国土数値情報 P29-23（令和5年度）
- 児童数: 吹田=令和7年版吹田市統計書（2025-05-01現在）、豊中=市教委在籍児童数調査票（2026-05-01現在）
  - 出典URLは tools/students.json に記載

### A27の元データに対する補正（build_data.py内で実施・重要）
- 「弘済小学校」の校区 → 実は**古江台小学校**の校区（住所一致で確認したラベル誤り）
- 「山田第五小学校」の校区が2件 → 片方は**山田第三**の校区。さらに山田第五は2025年3月閉校・山田第三へ統合したため両方を山田第三に合算
- 豊中「庄内小学校」→ **庄内さくら学園**（2022統合・2024から野田町1-1新校舎）へ合算
- 豊中「庄内南・庄内西・千成」→ **庄内よつば学園**（2026年4月開校・千成町2-2-65）へ合算

## 再生成の手順（児童数の年度更新など）
1. tools/students.json の数値・出典を更新
2. A27/P29のGeoJSONを国土数値情報からDL（`A27-23_27_GML.zip`等、zip内のgeojsonを取り出す。ファイル名はcp932）
3. `python3 tools/build_data.py <a27.geojson> <p29.geojson>`

## 残タスク・拡張候補
- 周辺市（箕面・池田・摂津など）の追加（優先度低と確認済み）
- チア生徒の在籍数の重ね表示（今回は「児童数=学校の児童数」で確定）
