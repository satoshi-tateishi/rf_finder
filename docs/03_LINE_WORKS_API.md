# LINE WORKS API 連携ガイド

LINE WORKS Bot API および構成員情報の取得に関する技術リファレンス。

## 1. 認証 (Service Account)

サーバーサイドから API を呼び出すための認証手順。

### アクセストークンの取得
- **Endpoint**: `POST https://auth.worksmobile.com/oauth2/v2.0/token`
- **Method**: `POST`
- **Headers**:
    - `Content-Type`: `application/x-www-form-urlencoded`
- **Parameters**:
    - `assertion`: 生成した JWT (RS256)
    - `grant_type`: `urn:ietf:params:oauth:grant-type:jwt-bearer`
    - `client_id`: Developer Console で発行された Client ID
    - `client_secret`: Developer Console で発行された Client Secret
    - `scope`: `bot`, `user.read`, `directory.read` など

---

## 2. 構成員情報の取得 (Users API)

アクセストークンを使用して、ユーザーの詳細情報を取得する。

### 構成員情報の取得
- **Endpoint**: `GET https://www.worksapis.com/v1.0/users/{userId}`
- **Headers**:
    - `Authorization`: `Bearer {access_token}`
- **Path Parameters**:
    - `userId`: 構成員の ID (メールアドレス等)

### 主なレスポンス項目
- `userId`: ユーザーID
- `userName`: 氏名 (`lastName`, `firstName`)
- `email`: メールアドレス
- `cellPhone`: 携帯電話番号

---

## 3. Bot API によるファイル送信

サーバー側から特定のトークルーム (channelId) へ PDF を送信する手順。

### 3.1 ファイルのアップロード
1. **アップロード URL の取得**:
   - `POST https://www.worksapis.com/v1.0/bots/{botId}/attachments`
   - Body: `{"fileName": "request.pdf"}`
   - Response: `uploadUrl`, `fileId`
2. **バイナリのアップロード**:
   - `POST {uploadUrl}`
   - `Content-Type`: `multipart/form-data`
   - Form field: `FileData` にバイナリをセット。

### 3.2 メッセージの送信
- **Endpoint**: `POST https://www.worksapis.com/v1.0/bots/{botId}/channels/{channelId}/messages`
- **Body (File)**:
```json
{
  "content": {
    "type": "file",
    "fileId": "{fileId}"
  }
}
```
- **Body (Text)**:
```json
{
  "content": {
    "type": "text",
    "text": "Your message here"
  }
}
```

---

## 4. 自動通知機能

メール送信時に、特定の LINE WORKS グループへ通知を送る機能を実装しています。

### 設定方法
`.env` ファイルに以下の設定を追加します。
- `LINE_WORKS_NOTIFICATION_CHANNEL_ID`: 通知を送るグループのトークルーム ID。

### 動作
1.  メール送信が成功すると、上記 ID のトークルームに通知メッセージが送信されます。
2.  続けて、メールに添付したものと同じ PDF ファイルが送信されます。

## 4. メニュー管理コマンド

本プロジェクトでは、Bot のメニューを管理するための Django 管理コマンドを実装しています。

### コマンドの実行
```bash
# 固定メニュー（Persistent Menu）の設定
docker exec rf_finder_web python manage.py setup_line_bot

# メニューの削除
docker exec rf_finder_web python manage.py setup_line_bot --delete
```

### 実装の詳細
- `apps/adjustments/services/line_bot_service.py`: API 呼び出しの本体（シングルトン、キャッシュ対応）。
- `apps/adjustments/management/commands/setup_line_bot.py`: コマンドラインインターフェース。
