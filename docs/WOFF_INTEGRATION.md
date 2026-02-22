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
- `woff.getChannelId()`: 現在のトークルームの `channelId` を取得 (モバイル版のみ)。
- `woff.sendMessage()`: トークルームへのメッセージ送信。
- `woff.isInClient()`: LINE WORKS アプリ内かどうかの判定。
- `woff.closeWindow()`: WOFF ウィンドウを閉じる。

---

## 2. 実装プラン (Phases)

リファクタリング済みのアーキテクチャに基づき、以下のフェーズで実装を進めます。

### Phase 1: SDK 導入と基盤実装 (Completed)
まずは WOFF として動作するための最小限のセットアップを行います。
- [x] **SDK の読み込み**: `index.html` への script タグ追加。
- [x] **初期化ロジックの実装**: `static/js/woff-service.js` の作成。
- [x] **デバッグ環境の整備**: ngrok による HTTPS トンネリング。

### Phase 2: ユーザー情報の自動連携 (Completed)
ユーザーの手入力を減らし、利便性を向上させます。
- [x] **プロフィール取得**: `woff.getProfile()` およびサーバーサイド API による詳細情報の取得。
- [x] **フォームの自動補完**: 
    - 取得した `userName` を「氏名」に、`phoneticUserName`（ひらがな変換済）を「ふりがな」に、`privateEmail` を「E-mail」に、`telephone/cellPhone` を「Tel」に自動セット。
- [x] **DB 連携**: `WoffUser` モデルへの情報の保存・更新。

### Phase 3: トークルームへの完了通知 (Completed)
申請が完了したことを、ユーザーが意識せずにトークルームへ共有します。
- [x] **送信完了メッセージ**: 
    - メール送信成功のコールバック内で `woff.sendFlexMessage()` を実行。
    - 催事名、使用者、施設リストを含むリッチなカード形式での通知を実装。

### Phase 4: Bot API 連携とセキュリティの最適化 (Completed)
本番運用に向けた信頼性と利便性の向上。

- [x] **Bot API によるファイル送信**:
    - サーバーサイド (`apps/adjustments/services/line_bot_service.py`) で LINE WORKS Bot API を使用してトークルームへ PDF ファイルを直接送信する機能を実装。
    - フロントエンド (`static/js/woff-service.js`) から `woff.getChannelId()` で取得した `channelId` をサーバーへ渡す仕組みを構築。
- [x] **署名検証 (Signature Verification)**:
    - `apps/facilities/views.py` の `index` ビューで `timestamp`, `nonce`, `signature` を使用し、WOFF URL からのリダイレクトであることの検証を実装。
    - 検証失敗時には、フロントエンドに警告を表示。
- [x] **ウィンドウ制御**:
    - 送信完了後、`woff.closeWindow()` で WOFF アプリのウィンドウが自動的に閉じる UX を提供 (`static/js/adjustment-form.js`)。
- [x] **UI/デバッグのクリーンアップ**:
    - `templates/index.html` からテスト用ボタンやデバッグバーを削除。
    - **デバッグ用テスト機能の追加**: 開発・デバッグ用に「Test Msg (テキスト)」および「Test PDF (ファイル)」送信ボタンを UI (`templates/index.html`) に再導入。
        - これらのボタンは `static/js/woff-service.js` および `static/js/api.js` からバックエンドの新しい API エンドポイント (`/api/adjustments/test-send-text-message/`, `/api/adjustments/test-send-pdf-message/`) を呼び出す。
        - モバイル環境での `channelId` 取得のデバッグを容易にするため、`woff.getChannelId()` の結果をバックエンドに送信しログに記録する機能 (`/api/adjustments/log-woff-channel-id-result/`) を追加。

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

## 7. Bot API によるファイル送信 (Server-side)

サーバー側から特定のトークルーム (channelId) へ PDF を送信する際の手順。

### 7.1 認証 (Service Account)
- **Endpoint**: `POST https://auth.worksmobile.com/oauth2/v2.0/token`
- **Auth Type**: JWT (RS256)
- **Required Scopes**: `bot`, `bot.message`

### 7.2 ファイルのアップロード
1. **アップロード URL の取得**:
   - `POST https://www.worksapis.com/v1.0/bots/{botId}/attachments`
   - Body: `{"fileName": "request.pdf"}`
   - Response: `uploadUrl`, `fileId`
2. **バイナリのアップロード**:
   - `POST {uploadUrl}`
   - `Content-Type`: `multipart/form-data`
   - Form field: `FileData` にバイナリをセット。

### 7.3 メッセージの送信
- **Endpoint**: `POST https://www.worksapis.com/v1.0/bots/{botId}/channels/{channelId}/messages`
- **Body**:
```json
{
  "content": {
    "type": "file",
    "fileId": "{fileId}"
  }
}
```

---

## 8. 実装のヒント
（再掲）

- **SSO 連携**: 外部ブラウザでユーザー情報を取得したい場合は `woff.isLoggedIn()` でチェックし、必要に応じて `woff.login()` を呼び出す。
- **デバッグ**: WOFF ブラウザ上ではブラウザのコンソールが見えないため、VConsole などの導入を検討する。
- **セキュリティ**: WOFF URL からの遷移であることを検証するため、サーバーサイドで `signature` の検証を行うことが推奨される。
