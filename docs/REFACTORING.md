# リファクタリングプラン: 特ラ運用調整支援アプリ

プロジェクトの健全性と保守性を維持するため、以下のフェーズに分けたリファクタリングを提案します。

## Phase 1: サービス層の分離と責務の明確化
現在の `apps/adjustments/services.py` は、Excel生成、PDF変換、メール送信の3つの大きな責務を抱えています。これらを分離し、単一責任原則（SRP）を適用します。

- [ ] **ファイルの分割**:
    - `excel_services.py`: `openpyxl` を使用した転記ロジック。
    - `pdf_services.py`: LibreOffice を使用した変換ロジック。
    - `email_services.py`: `EmailMessage` とテンプレート置換ロジック。
- [ ] **共通ユーティリティの抽出**:
    - `format_channels` などの汎用的な整形関数を `utils/formatters.py` 等へ移動。

## Phase 2: フロントエンドのモジュール化
現在、`templates/index.html` に JavaScript ロジック（約800行）が集中しています。これを機能単位で外部ファイルに分割し、メンテナンス性を向上させます。

- [ ] **JavaScript の外部化**:
    - `static/js/api.js`: Fetch API を使用したバックエンド通信。
    - `static/js/keep-list.js`: キープリストの管理と SortableJS の制御。
    - `static/js/adjustment-form.js`: 申請フォームの入力管理とバリデーション。
    - `static/js/ui-controller.js`: 画面遷移やバッジ表示などのDOM操作。
- [ ] **テンプレートの整理**:
    - モーダルや共通パーツを Django の `include` タグでコンポーネント化。

## Phase 3: データアクセスとエラーハンドリングの改善
`Member.objects.first()` のようなハードコードされたデータ取得や、各 View での場当たり的なエラーハンドリングを改善します。

- [ ] **共通ベースView/Mixinの導入**:
    - APIのレスポンス形式（成功・失敗）を統一するユーティリティの作成。
- [ ] **コンテキストプロセッサの活用**:
    - 会員情報（Member）を常にテンプレートで利用可能にする。
- [ ] **バリデーションの強化**:
    - フォームデータのバリデーションを `Django Forms` または `Serializers` に委ねる。

## Phase 4: テストカバレッジの向上
ロジックの変更による退行（デグレード）を防ぐため、重要な業務ロジックに対するテストを追加します。

- [ ] **業務ロジックのテスト**:
    - ガードバンド計算 (`calculate_available_frequencies`) の境界値テスト。
    - チャンネル整形ロジック (`format_channels`) のテスト。
- [ ] **ファイル生成のテスト**:
    - Excel/PDF が正常にバイナリとして生成されるかの疎通テスト。
- [ ] **メール送信のテスト**:
    - モックを使用したメール送信プロセスの検証。

## Phase 5: CI/CD と環境設定の最適化
- [ ] **環境変数の厳格化**:
    - `.env.example` の作成と、必須環境変数のチェック処理の追加。
- [ ] **静的解析の導入**:
    - `flake8` や `black` によるコードスタイルの統一。
- [ ] **Dockerの最適化**:
    - `Dockerfile` のマルチステージビルド検討（LibreOffice 依存によるイメージ肥大化の抑制）。
