# プロジェクト: 特ラ運用調整支援アプリ (RF Finder)

## 0. 基本方針
- **動作環境**: 本アプリケーションは Docker 環境で動作します。開発、テスト、デプロイは Docker コンテナ内で行うことを前提とします。
- **言語**: ユーザーへの回答および解説は、常に日本語で行うこと。
- **Playwright MCP**: UI の修正を行った際は、Playwright MCP を使用して自動的に表示チェックを行うこと。Playwright MCP の使用については、ユーザーからの事前の承諾が得られているものとする。

## 1. プロジェクト概要
特定ラジオマイク（A帯）の施設別空きチャンネル検索、運用調整届（PDF/Excel）の自動生成、および特ラ機構への自動メール送信を行うWebアプリケーション。

## 2. 技術スタック
- UI: Standalone Web App (HTML/JS/Tailwind CSS) ※LINE WORKS SSO連携予定
- Backend: Django (Python)
- Database: MySQL
- Libraries: reportlab (PDF), openpyxl (Excel), Pillow (Image)
- Infrastructure: Docker (開発・本番環境) / nginx / Let's Encrypt

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

   - 運用調整届 (PDF) のプレビュー表示および直接ダウンロード。
     - ファイル名規則: `運用連絡票_{区分}_{催事名}_{運用開始日}.pdf`

   - 特ラ機構への自動メール送信 (SMTP/SSL)。管理画面から宛先・CC・本文を柔軟に設定可能。

   - LINE WORKS Bot 連携 (PDF送信、メッセージ送信機能の基盤実装済み)。

   - ゼンハイザーWSM用CSV（セミコロン区切り）出力 (予定)。

## 5. コード品質とリファクタリング

- **アーキテクチャ**: サービス層のシングルトン化、Djangoキャッシュを利用したトークン管理。
- **UI/UX**: `showToast` による非同期通知、全画面PDFプレビューモーダル。
- **品質保証**: ユニットテスト完備 (LINE Bot Service, 業務ロジック, API)。
- **静的解析**: Ruff によるコード標準化。

## 6. ドキュメント

- **パス**: /Users/satoshi/rf_finder/docs

- **リファクタリング計画**: /Users/satoshi/rf_finder/docs/REFACTORING.md

- **データインポート手順**: /Users/satoshi/rf_finder/docs/DATA_IMPORT.md

- **PDF生成マッピング**: /Users/satoshi/rf_finder/docs/PDF_MAPPING.md

- **テスト・デバッグ手法**: /Users/satoshi/rf_finder/docs/TESTING.md

- **進捗状況**: /Users/satoshi/rf_finder/docs/PHASES.md
