import os
import sys
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- 安全装置: テストおよび開発環境の設定 ---
TESTING = 'test' in sys.argv

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
# .env で SECRET_KEY を必ず設定すること。未設定時は起動エラーになる。
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Proxy settings for generating correct absolute URLs
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF Trusted Origins (Django 4.0+)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost:8084', 'http://127.0.0.1:8084'])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'import_export',
    # Local apps
    'apps.facilities',
    'apps.adjustments',
    'apps.accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Added for static files without Apache
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # shin•on Portal の portal_jwt クッキーを検証して Django セッションに紐付ける
    # AuthenticationMiddleware の直後に配置することで、未認証時のみ JWT 認証を試みる
    'apps.accounts.middleware.PortalJWTMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {'default': env.db('DATABASE_URL', default='mysql://user:password@db:3306/rf_finder')}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# MEDIA_URL = 'media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Settings
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=10)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# LINE WORKS Bot API Settings（メッセージ通知用）
LINE_WORKS_CLIENT_ID = env('LINE_WORKS_CLIENT_ID', default='')
LINE_WORKS_CLIENT_SECRET = env('LINE_WORKS_CLIENT_SECRET', default='')
LINE_WORKS_SERVICE_ACCOUNT = env('LINE_WORKS_SERVICE_ACCOUNT', default='')
LINE_WORKS_PRIVATE_KEY_PATH = env('LINE_WORKS_PRIVATE_KEY_PATH', default='')

# Resolve relative path to absolute path using BASE_DIR
if not TESTING and LINE_WORKS_PRIVATE_KEY_PATH:
    if not os.path.isabs(LINE_WORKS_PRIVATE_KEY_PATH):
        full_key_path = os.path.join(BASE_DIR, LINE_WORKS_PRIVATE_KEY_PATH)
    else:
        full_key_path = LINE_WORKS_PRIVATE_KEY_PATH

    if os.path.exists(full_key_path):
        try:
            with open(full_key_path, 'r') as f:
                # Use .strip() to remove trailing newlines which can cause JWT parse errors
                LINE_WORKS_PRIVATE_KEY = f.read().strip()
        except Exception as e:
            print(f'Error reading private key: {e}')
            LINE_WORKS_PRIVATE_KEY = ''
    else:
        print(f'Private key file not found: {full_key_path}')
        LINE_WORKS_PRIVATE_KEY = ''
else:
    # テスト時やパス未設定時はダミーまたは空
    LINE_WORKS_PRIVATE_KEY = 'dummy_key_for_testing' if TESTING else ''

LINE_WORKS_BOT_ID = env('LINE_WORKS_BOT_ID', default='')
LINE_WORKS_NOTIFICATION_CHANNEL_ID = env('LINE_WORKS_NOTIFICATION_CHANNEL_ID', default='')

# Dropbox Backup Settings
DROPBOX_APP_KEY = env('DROPBOX_APP_KEY', default='')
DROPBOX_APP_SECRET = env('DROPBOX_APP_SECRET', default='')
DROPBOX_REDIRECT_URI = env('DROPBOX_REDIRECT_URI', default='http://localhost:8084/auth/dropbox/callback/')

# shin•on Portal JWT 連携設定
# PortalJWTMiddleware が portal_jwt クッキーを検証するために使用する
PORTAL_JWKS_URL = env('PORTAL_JWKS_URL', default='http://localhost/api/jwks/')
PORTAL_JWT_ISSUER = env('PORTAL_JWT_ISSUER', default='https://portal.shin-on1981.com')
PORTAL_JWT_AUDIENCE = env('PORTAL_JWT_AUDIENCE', default='shin-on-apps')
# 未認証時のリダイレクト先（開発: http://localhost/login/ / 本番: https://portal.shin-on1981.com/login/）
PORTAL_LOGIN_URL = env('PORTAL_LOGIN_URL', default='https://portal.shin-on1981.com/login/')
# ポータルトップURL（PORTAL_LOGIN_URL からパスを除いたベースURL）
PORTAL_URL = '/'.join(PORTAL_LOGIN_URL.split('/')[:3]) + '/'

# Apache リバースプロキシ背後での HTTPS 認識設定
# request.build_absolute_uri() が https:// を返すように設定
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- 本番セキュリティ設定 ---
# Apache が SSL 終端しているため SECURE_SSL_REDIRECT は不要
# Cookie は HTTPS 経由でのみ送信する（セッションハイジャック対策）
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# HSTS: ブラウザに1年間 HTTPS を強制させる
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

# --- セキュリティヘッダ ---
# X-Content-Type-Options: nosniff（MIME スニッフィング防止）
SECURE_CONTENT_TYPE_NOSNIFF = True
# Referrer-Policy: リファラー情報を同一オリジンのみに制限
SECURE_REFERRER_POLICY = 'same-origin'
# X-Frame-Options: クリックジャッキング対策（XFrameOptionsMiddleware が使用）
X_FRAME_OPTIONS = 'DENY'
# Content-Security-Policy: テンプレート内のインラインスクリプト・スタイルが存在するため
# 完全な CSP 適用にはテンプレートへの nonce 導入が必要。
# 現時点では上記3ヘッダで対応し、CSP は今後の課題とする。

# --- 一覧取得の上限設定 ---
FACILITY_SEARCH_LIMIT = 20
ADJUSTMENT_LIST_LIMIT = 20
AUDIT_LOG_LIST_LIMIT = 100

# --- 安全装置: テストおよび開発環境の設定 ---
if TESTING:
    # テスト実行時はメールをインメモリにする
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    # LINE WORKS API をモックモードにする
    LINE_WORKS_MOCK_MODE = True
    # その他、テスト時に制限したい項目があれば追加
