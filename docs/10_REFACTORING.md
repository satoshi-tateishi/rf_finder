# リファクタリング実績と今後の計画

本プロジェクトでは、保守性と堅牢性を向上させるため、段階的なリファクタリングを実施しました。

## 1. 完了済みのリファクタリング

### サービス層の分離と最適化
- **モジュール化**: `excel`, `pdf`, `email`, `line_bot`, `dropbox`, `wsm` の各サービスを独立させ、単一責任原則を適用。
- **シングルトン化**: `LineBotService` をシングルトン化し、Djangoキャッシュを用いたトークン管理を導入。
- **DRY化**: `json_api_view` デコレータを導入し、View層の共通処理（JSON解析、バリデーション）を統合。

### フロントエンドの刷新 (完了)
- **モジュール化**: 機能ごとに JS ファイルを分割（`api`, `keep-list`, `form-storage`, `pdf-preview`, `adjustment-form`, `app-state`, `form-service`, `validation-service`, `ui-renderers`, `ui-controller`, `notifications`, `constants`）。
- **[Step 7.1 完了] UI レンダリングの抽象化**: `ui-renderers.js` を導入。JS 内のインライン HTML 文字列を完全に排除し、DOM 生成ロジックを一元化。
- **[Step 7.2 完了] セントラルステート (State) による状態管理**: `app-state.js` を導入。グローバル変数を廃止し、申請 ID、ステータス、施設リスト、ユーザー情報等の一貫性を確保。画面遷移時の値保持やボタンロック状態の不整合を解消。
- **[Step 7.3 完了] ビジネスロジックと DOM 操作の完全分離**:
    - **FormService / ValidationService の抽出**: `collectFormData` を廃止し、データ収集と検証ロジックを独立。
    - **ドメインルールの厳格化**: 送信済みデータの完全ロック（サーバーサイド防御含む）、派生申請（変更・削除）の親子関係管理、催事名のロック機能を実装。
    - **バリデーションの高度化**: 同日内時間チェック、メール形式チェック、全施設選択チェックを統合。
    - **設計の安定化**: 初期化 (`createNewAdjustment`) と画面遷移 (`goToAdjustment`) の責務を分離。ID ベースのデータ紐付けによる堅牢なデータ収集を実現。
- **UX改善**: `showToast` による非同期通知、全画面 PDF プレビューモーダル、入力内容の自動保存・復元、ブラウザの「戻る」ボタン対策 (bfcache対応) を実装。

### 認証方式の刷新 (完了)
- **旧方式の削除**: LINE WORKS OIDC (Authorization Code Flow) + OTP の独自実装を全廃。
- **新方式への移行**: shin•on Portal 発行の `portal_jwt` クッキーを検証する `PortalJWTMiddleware` に一本化。
    - PyJWKClient による JWKS 経由の RS256 署名検証。
    - `portal_uuid` による UserProfile の自動検索・リンク。
- **Apache mod_auth_mellon 依存の解消**: Portal 集中認証への移行により不要となった。

### 信頼性と品質の向上
- **バリデーションの強化**: Django Forms とフロントエンド二重チェックによる厳格な入力検証。
- **出力の動的化**: PDF/Excel の命名規則を自動生成。
- **セキュリティの強化**: 送信済みデータの不変化、下書きの所有権チェック、施設 ID の整合性検証をサーバーサイドで実装。
- **静的解析**: `ruff` によるコード標準化。
- **Tailwind CSS のローカルビルド化**: CDN 依存を排除し、本番環境でのセキュリティと安定性を向上。

### バックエンドのロジック集約 (Fat View の解消)
- **モデルへの移譲**: `OperationAdjustment` モデルに JSON データの永続化ロジック (`save_from_json`) を移行し、トランザクション管理 (`transaction.atomic`) を導入。
- **通知メッセージの抽象化**: `LineBotService` に通知文面の構築ロジックをカプセル化し、「現地使用者」と「申請者（操作ユーザー）」の明示的区別を導入。

---

## 2. 残課題

### □ フロントエンド (Phase 8.3)
- [ ] **修正・再送信フローの充実**: 過去データからのコピー作成、ステータス管理と履歴表示の改善。

### □ バックエンド・インフラ
- [ ] **定数管理の統合**: `apps/adjustments/constants.py` への申請区分・チャンネル定義の完全集約。
- [ ] **Docker セキュリティ**: 実行ユーザーの非 root 化。

### □ テスト
- [ ] **accounts / facilities アプリのテスト**: 現状テストが未実装。主要なビューとモデルのテストを追加する。
- [ ] **Playwright E2E テスト**: UI の統合テストを実装する。
