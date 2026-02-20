# リファクタリングプラン: 特ラ運用調整支援アプリ

プロジェクトの健全性と保守性を維持するため、以下のフェーズに分けたリファクタリングを提案します。

## Phase 1: サービス層の分離と責務の明確化 (完了)
現在の `apps/adjustments/services.py` を分離し、単一責任原則（SRP）を適用しました。

- [x] **ファイルの分割**:
    - `excel_services.py`: `openpyxl` を使用した転記ロジック。
    - `pdf_services.py`: LibreOffice を使用した変換ロジック。
    - `email_services.py`: `EmailMessage` とテンプレート置換ロジック。
- [x] **共通ユーティリティの抽出**:
    - `format_channels` などの汎用的な整形関数を `apps/adjustments/utils.py` へ移動。

## Phase 2: フロントエンドのモジュール化 (完了)
`templates/index.html` に集中していた JavaScript ロジックを機能単位で外部ファイルに分割し、メンテナンス性を向上させました。

- [x] **JavaScript の外部化**:
    - `static/js/api.js`: Fetch API を使用したバックエンド通信モジュール。
    - `static/js/keep-list.js`: キープリストの管理と SortableJS の制御モジュール。
    - `static/js/adjustment-form.js`: 申請フォームの入力管理とアクション制御モジュール。
    - `static/js/ui-controller.js`: 画面描画やイベント監視などのUI制御モジュール。
- [x] **テンプレートの整理**:
    - `index.html` から約800行のロジックを削除し、外部ファイルの読み込みへ移行。

## Phase 3: データアクセスとエラーハンドリングの改善
`Member.objects.first()` のようなハードコードされたデータ取得や、各 View での場当たり的なエラーハンドリングを改善します。

- [ ] **共通ベースView/Mixinの導入**:
    - APIのレスポンス形式（成功・失敗）を統一するユーティリティの作成。
- [ ] **コンテキストプロセッサの活用**:
    - 会員情報（Member）を常にテンプレートで利用可能にする。
- [ ] **バリデーションの強化**:
    - フォームデータのバリデーションを `Django Forms` または `Serializers` に委ねる。

## Phase 4: テストカバレッジの向上 (進行中)
ロジックの変更による退行（デグレード）を防ぐため、重要な業務ロジックに対するテストを追加しました。

- [x] **業務ロジックのテスト**:
    - ガードバンド計算 (`calculate_available_frequencies`) の境界値テスト。
    - チャンネル整形ロジック (`format_channels`) のテスト。
- [x] **ファイル生成のテスト**:
    - Excel/PDF が正常にバイナリとして生成されるかの疎通テスト。
- [x] **メール送信のテスト**:
    - モックを使用したメール送信プロセスの検証。
- [ ] **フロントエンドのテスト**:
    - Playwright MCP 等を使用した UI テストの自動化。

## Phase 5: CI/CD と環境設定の最適化
- [ ] **環境変数の厳格化**:
    - `.env.example` の作成と、必須環境変数のチェック処理の追加。
- [ ] **静的解析の導入**:
    - `flake8` や `black` によるコードスタイルの統一。
- [ ] **Dockerの最適化**:
    - `Dockerfile` のマルチステージビルド検討（LibreOffice 依存によるイメージ肥大化の抑制）。
