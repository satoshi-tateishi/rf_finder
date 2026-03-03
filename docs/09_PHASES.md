# プロジェクト進行状況: 特ラ運用調整支援アプリ

## Phase 1: 基盤構築とデータインポート (完了)
- [x] Docker環境 (Django, MySQL) の構築
- [x] データモデル設計 (`Facility`, `TVChannelStatus`, `WirelessEquipment`)
- [x] 総務省CSV (`locations.csv`, `devices.csv`) のインポートスクリプト実装
- [x] ch53の自動補完ロジック実装
- [x] 文字コード (`utf8mb4`) および kHz 単位での周波数運用設定

## Phase 2: 業務ロジックとAPIの実装 (完了)
- [x] ガードバンド (GB) 計算エンジンの実装
    - 隣接ch不可時の1MHz GB適用
    - ch13下限/ch53上限の例外処理
- [x] 施設検索API (`applied_area`, `category` を含む)
- [x] 施設詳細・利用可能チャンネル算出API
- [x] 郵便番号自動付与ロジック (`generate_facility_data.py`)

## Phase 3: フロントエンド UI 構築 (完了)
- [x] モバイルファーストのレスポンシブデザイン (Tailwind CSS ローカルビルド)
- [x] チャンネル状況のグリッド表示 (ch13-ch53)
- [x] デバイスインジケーター (各ch下の対応機器カバー範囲表示)
- [x] ガードバンドの視覚化
- [x] チャンネル選択機能 (タップによる選択状態の管理)
- [x] キープリスト機能 (複数施設の選択)
- [x] SortableJS による施設の並び替え
- [x] 郵便番号表示 (〒xxx-xxxx形式)

## Phase 4: 運用調整届 (PDF/Excel) とデータ書き出し (完了)
- [x] `openpyxl` と `master.xlsx` を使用したExcel書き出し機能の実装
- [x] ReportLab を使用した運用調整届PDFの自動生成 (プレビュー用)
- [x] 施設データのエクスポート機能の最適化 (インポート用CSVと互換性のある形式)
- [x] ブラウザからのExcelダウンロード機能
- [x] 申請情報入力フォーム (申請区分、現地使用者、催事名、使用日・時間、マイク数)
- [x] Sennheiser WSM用CSVエクスポート機能 (セミコロン区切り、GB自動計算)

## Phase 5: 管理機能と外部連携 (完了)
- [x] 会員情報 (Member) 管理機能の実装 (旧Companyモデルを刷新)
- [x] Django Admin UI のカスタマイズ
    - 施設・会員情報のカード形式表示
    - 入力フィールドのレイアウト調整
- [x] 特ラ機構への自動メール送信機能 (Port 465/SSL対応)
- [x] メールテンプレート管理機能 (動的プレースホルダー `{タイプ}` 等に対応)
- [x] CC機能の実装 (`{ユーザーEメールアドレス}` 等の自動補完対応)
- [x] 送信先アドレスの管理画面一元化（.env依存の解消）
- [x] メール送信時の LINE WORKS グループ通知機能 (メッセージ & PDF送信)

## Phase 6: リファクタリングと品質向上 (完了)
- [x] **バックエンドのリファクタリング**:
    - サービス層のシングルトン化とキャッシュ利用 (LineBotService)
    - 命名規則の統一 (`richmenuId` 等) と API エンドポイントの最新化
- [x] **フロントエンドのリファクタリング**:
    - WOFF依存コードの完全削除とスタンドアロンWebアプリ化
    - 非同期通知システム (`showToast`) の導入
    - 全画面PDFプレビューモーダルの実装
- [x] **品質保証**:
    - バックエンドのユニットテスト・結合テストの拡充
    - 静的解析ツール (`ruff`) の導入とコード標準化

## Phase 7: ブラッシュアップと本番デプロイ (完了)
- [x] **フロントエンド刷新 (Step 7.1〜7.3)**:
    - `ui-renderers.js` による UI レンダリングの抽象化
    - `app-state.js` によるセントラルステート管理
    - `FormService` / `ValidationService` の抽出によるビジネスロジックと DOM 操作の分離
- [x] **UI/UX の微調整**: ナビバーへの shin•on Portal リンク追加、操作感の向上
- [x] **本番用ドメイン/SSL (Let's Encrypt)** 設定完了
- [x] **shin•on Portal Apache ゲートウェイ連携**: `shin-on-internal` 外部ネットワーク経由で `apache-gateway` コンテナからのリバースプロキシを受け付け、`SECURE_PROXY_SSL_HEADER` による HTTPS 認識を設定
- [x] **GitHub Actions 自動デプロイ** 設定完了
- [x] **本番起動時の自動処理**: `migrate` と `collectstatic` の自動実行 (docker-compose.prod.yml)
- [x] **最終動作確認** 完了

## Phase 8: 運用データの永続化と認証連携 (ほぼ完了)
- [x] **Phase 8.1: 運用申請データの保存・再編集機能 (Persistence)**
    - [x] `OperationAdjustment` モデルの拡張（全入力項目の保存対応）
    - [x] 保存・更新用APIエンドポイントの実装
    - [x] フロントエンド：保存ボタンの実装と保存済みデータの読込
    - [x] 検索・一覧機能の実装（催事名、施設名、作成者、スクロール表示対応）
    - [x] **UI/UX 改善**:
        - [x] カスタム意思決定モーダル（showDecisionModal）の実装
        - [x] 送信済みデータからの「変更・削除」申請作成フローの自動化
- [x] **Phase 8.2: shin•on Portal JWT 認証連携 (Authentication)**
    - [x] Portal JWT ミドルウェア (`PortalJWTMiddleware`) の実装
        - PyJWKClient による JWKS エンドポイント経由の署名検証 (RS256)
        - `portal_jwt` クッキーの検証・自動ログイン
        - `portal_uuid` による UserProfile の自動検索・リンク
    - [x] ログイン必須化（未認証時は Portal ログインへリダイレクト）
    - [x] ログインユーザーと `OperationAdjustment` の自動紐付け
    - [x] **権限（Role）システム**: `admin`, `editor`, `general`, `viewer` の役割設定と操作制限
    - [x] **旧 LINE WORKS SSO / OTP 認証の削除**: shin•on Portal に集約
- [ ] **Phase 8.3: 修正・再送信フローの確立 (Workflow)**
    - [ ] 過去データからのコピー作成機能の充実
    - [ ] ステータス管理と履歴表示の改善

## Phase 9: Dropbox バックアップ・復元機能 (完了)
- [x] `DropboxToken` モデルによる OAuth 2.0 トークン永続化
- [x] `DropboxService` によるチャンクアップロード・自動リフレッシュ
- [x] `fcntl` ファイルロックによる二重起動防止
- [x] Web UI からのバックアップ一覧表示・ワンクリック復元
- [x] Django 管理コマンド `backup_db` の実装
- [x] 保持ポリシー (直近5世代 + 月次3ヶ月アーカイブ)
