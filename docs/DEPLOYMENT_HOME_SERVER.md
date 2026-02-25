# 自宅サーバーデプロイガイド (RF Finder)

RF Finder (特ラ運用調整支援アプリ) を自宅サーバーの Docker 環境で公開し、GitHub Actions で自動デプロイする手順.

## 構成概要

```
インターネット → ルーター(80, 443, 56834) → 自宅サーバー
                                           ├─ Host Apache (SSL終端, リバースプロキシ, 静的ファイル配信)
                                           └─ Docker (RF Finder)
                                               ├─ web (Django/Gunicorn): 80 (Host: 8085)
                                               └─ db (MySQL:8.0): 3306 (Host: 3309)
```

**デプロイフロー**: `git push origin main` → GitHub Actions → SSH経由で本番サーバー更新

---

## 1. サーバー環境構築

### 必要パッケージ

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Apache (Host側)
sudo apt install -y apache2
sudo a2enmod proxy proxy_http headers ssl rewrite

# その他
sudo apt install -y certbot python3-certbot-apache fail2ban ufw git
```

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

| ドメイン | アプリ | ポート | 備考 |
|-------------|--------|--------|------|
| `rff.shin-on1981.com` | RF Finder | 8085 | 特定ラジオマイク運用調整支援 |

**ルーター ポートフォワーディング**:
- 80 (HTTP) -> サーバー:80
- 443 (HTTPS) -> サーバー:443
- 56834 (SSH) -> サーバー:56834

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
# ディレクトリ作成
sudo mkdir -p /var/www/rf_finder
# 所有者を現在のユーザーに変更
sudo chown $USER:$USER /var/www/rf_finder
```

### 2. リポジトリのクローン
```bash
cd /var/www/rf_finder
# 既に公開鍵がGitHubに登録されている前提
git clone git@github.com:satoshi-tateishi/rf_finder.git .
```

### 3. 環境変数 (.env) の作成
Git管理外の秘密情報（パスワードやAPIキー）を設定します.
```bash
cp .env.sample .env
nano .env
```
※ `DEBUG=False` や本番用ドメイン、DBパスワードを適切に設定してください.

### 4. 初回起動と初期化
```bash
# Dockerコンテナ起動 (本番用設定ファイルを指定)
docker compose -f docker-compose.prod.yml up -d

# データベースマイグレーション
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# 静的ファイルの集約 (ホスト側の static/ に集約される)
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# 管理者作成 (管理画面へのログイン用)
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

---

## 5. 自動デプロイの設定 (GitHub Actions)
初回デプロイが完了したら、以降の更新は `git push` で自動化できます.
`.github/workflows/deploy.yml`（未作成の場合は作成）に、`/var/www/rf_finder` で `git pull` とコンテナ再起動を行う設定を追加してください.

---

## 6. Host Apache & SSL設定

Host側のApacheをリバースプロキシとして設定し、静的ファイルを配信しつつSSLを終端します.

### 1. SSL証明書の取得
```bash
sudo certbot certonly --apache -d rff.shin-on1981.com
```

### 2. VirtualHost設定の作成
`/etc/apache2/sites-available/rff-finder.conf`:

```apache
<VirtualHost *:80>
    ServerName rff.shin-on1981.com
    RewriteEngine on
    RewriteCond %{SERVER_NAME} =rff.shin-on1981.com
    RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>

<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName rff.shin-on1981.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/rff.shin-on1981.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/rff.shin-on1981.com/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf

    # 静的ファイルの配信 (ホスト側のディレクトリを直接指定)
    Alias /static/ /var/www/rf_finder/static/
    <Directory "/var/www/rf_finder/static">
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    # 静的ファイル以外はDockerのDjangoコンテナ(ポート8085)へ転送
    ProxyPreserveHost On
    ProxyPass /static/ !
    ProxyPass / http://localhost:8085/
    ProxyPassReverse / http://localhost:8085/

    # プロトコル情報をDjangoに伝えるためのヘッダー
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"

    ErrorLog ${APACHE_LOG_DIR}/rf_finder_error.log
    CustomLog ${APACHE_LOG_DIR}/rf_finder_access.log combined
</VirtualHost>
</IfModule>
```

### 3. 設定の有効化
```bash
sudo a2ensite rff-finder.conf
sudo apachectl configtest
sudo systemctl reload apache2
```

---

## 7. 運用・トラブルシューティング

### ログの確認
```bash
docker compose -f docker-compose.prod.yml logs -f web
```

### 静的ファイルの更新
CSSやJSを変更した後は、コンテナ内で `collectstatic` を実行する必要があります.
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### DBバックアップ
このプロジェクトには Dropbox への自動バックアップ機能が実装されています.
管理画面または `scripts/` 内のスクリプト（あれば）から実行可能です.

---

## 8. LINE WORKS SSO / OAuth 設定の注意

ドメインが `rff.shin-on1981.com` に変更されるため、LINE WORKS Developer Console の設定も更新が必要です.

- **Redirect URL**: `https://rff.shin-on1981.com/auth/lineworks/callback/`
- **Domain**: `rff.shin-on1981.com`
