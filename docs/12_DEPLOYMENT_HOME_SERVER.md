# 自宅サーバーデプロイガイド (RF Finder)

RF Finder (特ラ運用調整支援アプリ) を自宅サーバーの Docker 環境で公開し、GitHub Actions で自動デプロイする手順.

## 構成概要

```
インターネット → ルーター(80, 443, 56834) → 自宅サーバー
                                           └─ Docker
                                               ├─ shin•on Portal アプリ
                                               │   └─ apache-gateway (SSL終端, リバースプロキシ)
                                               │       ├─ portal.shin-on1981.com → portal_web
                                               │       └─ rff.shin-on1981.com   → rf_finder_web ←─┐
                                               └─ RF Finder アプリ (このリポジトリ)               │
                                                   ├─ rf_finder_web (Django/Gunicorn): 80 ────────┘
                                                   └─ rf_finder_db (MySQL:8.0): 3306
```

**ポイント**:
- RF Finder の `docker-compose.yml` に Apache は含まれない。
- SSL終端・リバースプロキシはすべて **shin•on Portal の `apache-gateway` コンテナ** が担う。
- 両アプリは外部 Docker ネットワーク `shin-on-internal` で接続される。

**デプロイフロー**: `git push origin main` → GitHub Actions → SSH経由で本番サーバー更新

---

## 1. サーバー環境構築

### 必要パッケージ

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# その他
sudo apt install -y fail2ban ufw git
```

> Apache は shin•on Portal アプリ側の Docker コンテナとして管理されます。
> ホスト側への Apache インストールは不要です。

### セキュリティ設定 (ufw)

```bash
sudo ufw default deny incoming
sudo ufw allow 56834/tcp  # SSH（カスタムポート）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 2. ネットワーク設定

### MyDNS.JP サブドメイン設定

RF Finder は独自ドメイン `rff.shin-on1981.com` でアクセスします.

| ドメイン | アプリ | 備考 |
|-------------|--------|------|
| `rff.shin-on1981.com` | RF Finder | 特定ラジオマイク運用調整支援 |

**ルーター ポートフォワーディング**:
- 80 (HTTP) -> サーバー:80
- 443 (HTTPS) -> サーバー:443
- 56834 (SSH) -> サーバー:56834

### Docker ネットワークの事前作成

shin•on Portal の `apache-gateway` コンテナと RF Finder の `rf_finder_web` コンテナを接続するための外部ネットワーク。**shin•on Portal のデプロイ前に作成しておく**。

```bash
docker network create shin-on-internal
```

---

## 3. GitHub設定

### デプロイキー作成（サーバー側）

```bash
ssh-keygen -t ed25519 -C "deploy@rf-finder" -f ~/.ssh/id_ed25519_deploy_rf -N ""
cat ~/.ssh/id_ed25519_deploy_rf.pub >> ~/.ssh/authorized_keys
```

### GitHub Secrets設定

| Secret名 | 値 |
|---------|---|
| `DEPLOY_HOST` | rff.shin-on1981.com |
| `DEPLOY_USER` | (サーバーのユーザー名) |
| `DEPLOY_KEY` | `~/.ssh/id_ed25519_deploy_rf` の内容 |
| `DEPLOY_PATH` | /var/www/rf_finder |

#### SSH接続でエラー（Permission denied）が出る場合
`git clone` 時にエラーが出る場合は、以下の手順で鍵の有効化を確認してください.

1. **GitHubへの登録確認**:
   `cat ~/.ssh/id_ed25519_deploy_rf.pub` の内容が GitHubリポジトリの [Settings] > [Deploy keys] に正確に登録されているか確認.
2. **SSHエージェントへの追加**:
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519_deploy_rf
   ```
3. **SSH設定の固定化 (推奨)**:
   毎回 `ssh-add` するのを避けるため、`~/.ssh/config` に以下を記述します.
   ```text
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_ed25519_deploy_rf
   ```

---

## 4. 初回デプロイ (サーバー側での手動設定)

自動デプロイを開始する前に、初回のみサーバー側で手動のディレクトリ作成と `.env` 設定が必要です.

### 1. プロジェクトディレクトリの作成と権限設定
```bash
sudo mkdir -p /var/www/rf_finder
sudo chown $USER:$USER /var/www/rf_finder
```

### 2. リポジトリのクローン
```bash
cd /var/www/rf_finder
git clone git@github.com:satoshi-tateishi/rf_finder.git .
```

### 3. 環境変数 (.env) の作成
Git管理外の秘密情報（パスワードやAPIキー）を設定します.
```bash
cp .env.sample .env
nano .env
```
※ `DEBUG=False` や本番用ドメイン、DBパスワードを適切に設定してください.

### 4. 初回起動

`migrate` と `collectstatic` は起動時に自動実行されます。

```bash
# Dockerコンテナ起動 (本番用設定ファイルを指定)
docker compose -f docker-compose.prod.yml up -d

# 管理者作成 (初回のみ)
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

> **注意**: shin•on Portal アプリが先に起動して `apache-gateway` コンテナが存在し、`shin-on-internal` ネットワークが作成済みであることを確認してから起動してください。

---

## 5. 自動デプロイの設定 (GitHub Actions)

初回デプロイが完了したら、以降の更新は `git push` で自動化できます.
`.github/workflows/deploy.yml` に `/var/www/rf_finder` で `git pull` とコンテナ再起動を行う設定を追加してください.

---

## 6. Apache リバースプロキシ設定 (shin•on Portal 側)

RF Finder 用の Apache バーチャルホスト設定は **shin•on Portal リポジトリ** で管理します。
`rff.shin-on1981.com` へのリクエストを `rf_finder_web` コンテナ（`shin-on-internal` ネットワーク経由）に転送する設定例:

```apache
<VirtualHost *:443>
    ServerName rff.shin-on1981.com

    SSLEngine on
    # ... SSL証明書設定 ...

    # 静的ファイルの配信
    Alias /static/ /var/www/rf_finder/static_root/
    <Directory "/var/www/rf_finder/static_root">
        Require all granted
    </Directory>

    # Django コンテナへのプロキシ (コンテナ名で名前解決)
    ProxyPreserveHost On
    ProxyPass /static/ !
    ProxyPass / http://rf_finder_web:80/
    ProxyPassReverse / http://rf_finder_web:80/

    # プロトコル情報をDjangoに伝えるためのヘッダー
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
</VirtualHost>
```

> `rf_finder_web` はコンテナ名。`shin-on-internal` ネットワークで接続されているため、コンテナ名による名前解決が可能。

---

## 7. 運用・トラブルシューティング

### 起動・停止・削除
```bash
# 起動 (バックグラウンド)
docker compose -f docker-compose.prod.yml up -d

# 停止のみ (コンテナは残る)
docker compose -f docker-compose.prod.yml stop

# 停止と削除
docker compose -f docker-compose.prod.yml down

# 停止・削除に加え、データ(ボリューム)も完全にリセットする場合 ※注意
docker compose -f docker-compose.prod.yml down -v
```

### ログの確認
```bash
docker compose -f docker-compose.prod.yml logs -f web
```

### DBマイグレーション (手動実行が必要な場合)
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 静的ファイルの更新 (手動実行が必要な場合)
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### DBバックアップ
Dropbox への自動バックアップ機能が実装されています.
Web UI のハンバーガーメニューから実行するか、以下のコマンドで手動実行できます.
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py backup_db
```
