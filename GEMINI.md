# プロジェクト: 特ラ運用調整支援アプリ (LINE WORKS WOFF)

## 0. 基本方針
- **言語**: ユーザーへの回答および解説は、常に日本語で行うこと。
- **Playwright MCP**: UI の修正を行った際は、Playwright MCP を使用して自動的に表示チェックを行うこと。Playwright MCP の使用については、ユーザーからの事前の承諾が得られているものとする。

## 1. プロジェクト概要
特定ラジオマイク（A帯）の施設別空きチャンネル検索、運用調整届（PDF）の自動生成、およびゼンハイザーWSM用データの書き出しを行うWebアプリケーション。

## 2. 技術スタック
- UI: LINE WORKS WOFF (HTML/JS/Tailwind CSS)
- Backend: Django (Python)
- Database: MySQL
- Libraries: reportlab (PDF), openpyxl (Excel)
- Infrastructure: Docker / nginx / Let's Encrypt

## 3. 重要な業務ロジック・計算規則

### 3.1 周波数定義
- **TV ch13 ~ ch53**: 総務省公表の施設別リストに基づき、空き状況を判定。
- **計算対象範囲**: 各chの周波数幅（6MHz単位）およびガードバンド。

### 3.2 ガードバンド (GB) 適用ルール
隣接するTVチャンネルの利用状況に基づき、動的に使用可能範囲を制限する。
1. **ch13の下限**: ガードバンドを設けない。
2. **ch53の上限**: ガードバンドを設けない。
3. **その他のチャンネル**:
   - 隣接するチャンネルが「使用不可能（TV放送等）」な場合、その隣接側に対して **1MHzのガードバンド** を設定し、マイクの配置を禁止する。
   - 例: ch20が使用可能、ch21が使用不可の場合、ch20の上限1MHz分は使用不可とする。

## 4. 主要機能要件

1. **データインポート**: 総務省Excel(CSV変換後)の取り込み。郵便番号の自動付与 (`generate_facility_data.py`)。ch53データの補完。

2. **施設検索**: 複数施設選択（キープリスト）、適用エリア・住所・郵便番号検索。

3. **視覚化**: チャンネル空き状況をカラーバーで表示。機器スペック（設定可能周波数）をオーバーライド。

4. **外部連携**: 

   - 特ラ機構指定Excel (`master.xlsx`) への転記・ダウンロード。

   - 上記Excelデータに基づく運用調整届 (PDF) のプレビュー表示。

   - LINE WORKSトークルームへの送信 (予定)。

   - 特ラ機構への自動メール送信 (予定)。

   - ゼンハイザーWSM用CSV（セミコロン区切り）出力 (予定)。



## 5. ドキュメント

- **パス**: /Users/satoshi/rf_finder/docs

- **データインポート手順**: /Users/satoshi/rf_finder/docs/DATA_IMPORT.md

- **PDF生成マッピング**: /Users/satoshi/rf_finder/docs/PDF_MAPPING.md

- **テスト・デバッグ手法**: /Users/satoshi/rf_finder/docs/TESTING.md

- **進捗状況**: /Users/satoshi/rf_finder/docs/PHASES.md
