# LINE WORKS WOFF 連携ガイド & 実装プラン

LINE WORKS WOFF (WORKS Front-end Framework) をプロジェクトに組み込むための調査メモと実装フェーズ。

## 1. WOFF の概要と主要機能

### SDK の導入
HTML の `<head>` または `<body>` 末尾で SDK を読み込む。
```html
<script charset="utf-8" src="https://static.worksmobile.net/static/wm/woff/edge/3.7.1/sdk.js"></script>
```

### 主要な API
- `woff.init()`: 初期化（必須）。
- `woff.getProfile()`: ユーザー名、ユーザーIDの取得。
- `woff.sendMessage()`: トークルームへのメッセージ送信。
- `woff.isInClient()`: LINE WORKS アプリ内かどうかの判定。
- `woff.closeWindow()`: WOFF ウィンドウを閉じる。

---

## 2. 実装プラン (Phases)

リファクタリング済みのアーキテクチャに基づき、以下のフェーズで実装を進めます。

### Phase 1: SDK 導入と基盤実装
まずは WOFF として動作するための最小限のセットアップを行います。
- [ ] **SDK の読み込み**: `index.html` への script タグ追加。
- [ ] **初期化ロジックの実装**: `static/js/woff-service.js`（新規）の作成。
    - `woff.init()` の実行とエラーハンドリング。
    - `woffId` を環境変数（`.env`）からテンプレート経由で渡す仕組みの構築。
- [ ] **デバッグ環境の整備**:
    - モバイルでの動作確認用ログ出力（VConsole 等）の検討。
    - HTTPS トンネリング（ngrok 等）の準備。

### Phase 2: ユーザー情報の自動連携
ユーザーの手入力を減らし、利便性を向上させます。
- [ ] **プロフィール取得**: `woff.getProfile()` によるユーザー情報の取得。
- [ ] **フォームの自動補完**: 
    - 取得した `displayName` を申請フォームの「現地使用者：氏名」に自動セット。
    - WOFF 経由でのアクセス時のみ、初期値を上書きする。
- [ ] **DB 連携**: `WoffUser` モデルへのマッピング。

### Phase 3: トークルームへの完了通知
申請が完了したことを、ユーザーが意識せずにトークルームへ共有します。
- [ ] **送信完了メッセージ**: 
    - メール送信成功のコールバック内で `woff.sendMessage()` を実行。
    - 「【RF Finder】運用調整届を送信しました（催事名：XXX）」といった通知を投稿。
- [ ] **Flex Message へのアップグレード**:
    - より視覚的に分かりやすい形式での通知（リッチなカード形式）。

### Phase 4: セキュリティと UX の最適化
本番運用に向けた信頼性と使い勝手の向上。
- [ ] **署名検証 (Signature Verification)**:
    - サーバーサイドでの `signature` チェック。不正な直接アクセスを防止。
- [ ] **ウィンドウ制御**:
    - 送信完了後、数秒待ってから `woff.closeWindow()` で自動的に閉じる。
- [ ] **エラーハンドリングの徹底**:
    - 外部ブラウザでの起動時（SSO ログインが必要な場合）の誘導。

---

## 3. 開発環境の構築 (HTTPS対応)

WOFF はセキュリティ上の理由から **HTTPS 必須** です。ローカル開発環境 (`localhost:8084`) を LINE WORKS と連携させるには、`ngrok` 等のトンネリングツールを使用して一時的に HTTPS 公開する必要があります。

### ngrok を使用した手順
1.  **トンネルの起動**:
    ```bash
    ngrok http 8084
    ```
2.  **URLの取得**:
    `https://xxxx-xxxx.ngrok-free.app` のような URL が発行されます。
3.  **Developer Console への登録**:
    LINE WORKS Developer Console の WOFF アプリ設定で、**Endpoint URL** に上記 URL を登録します。
    ※ トンネルを再起動するたびに URL が変わるため（無料版）、その都度 Console の更新が必要です。

---

## 5. ユーザー情報の取得 (Server-side API)

WOFF で取得したアクセストークンを使用して、サーバーサイドからより詳細なユーザー情報を取得する場合、以下の API を使用します。

### 構成員情報の取得
- **Endpoint**: `GET https://www.worksapis.com/v1.0/users/{userId}`
- **Method**: `GET`
- **Headers**:
    - `Authorization`: `Bearer {access_token}`
- **Path Parameters**:
    - `userId`: 構成員の ID (メールアドレスまたは resourceId)
- **Required Scopes**:
    - `user`, `user.read`, `directory`, `directory.read` のいずれか

### 主なレスポンス項目
- `userId`: ユーザーID
- `userName`: 氏名 (`lastName`, `firstName`)
- `email`: メールアドレス
- `organizations`: 所属組織情報
- `cellPhone`: 携帯電話番号

---

## 6. 実装のヒント
（再掲）

- **SSO 連携**: 外部ブラウザでユーザー情報を取得したい場合は `woff.isLoggedIn()` でチェックし、必要に応じて `woff.login()` を呼び出す。
- **デバッグ**: WOFF ブラウザ上ではブラウザのコンソールが見えないため、VConsole などの導入を検討する。
- **セキュリティ**: WOFF URL からの遷移であることを検証するため、サーバーサイドで `signature` の検証を行うことが推奨される。
