import logging
import random
import uuid
from datetime import timedelta

import jwt
import requests
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.adjustments.services import LineBotService

from .models import UserProfile
from .utils import normalize_phonetic

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('facilities:index')
    return render(request, 'login.html')


def lineworks_login(request):
    # State生成
    state = str(uuid.uuid4())
    request.session['oidc_state'] = state

    # パラメータ取得
    client_id = settings.LINE_WORKS_CLIENT_ID
    redirect_uri = settings.LINE_WORKS_REDIRECT_URI
    domain = getattr(settings, 'LINE_WORKS_DOMAIN', 'shin-on1981')

    auth_base = "https://auth.worksmobile.com/oauth2/v2.0/authorize"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "response_type": "code",
        "state": state,
        "domain": domain
    }

    # URL生成
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return redirect(f"{auth_base}?{query}")


def lineworks_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    if error:
        logger.error(f"LINE WORKS Auth Error: {error}")
        return render(request, 'login.html', {'error': '認証がキャンセルされたか、エラーが発生しました。'})

    if not code or state != request.session.get('oidc_state'):
        return render(request, 'login.html', {'error': '不正な遷移です（State不一致）。'})

    # Token交換
    token_url = "https://auth.worksmobile.com/oauth2/v2.0/token"
    payload = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": settings.LINE_WORKS_CLIENT_ID,
        "client_secret": settings.LINE_WORKS_CLIENT_SECRET,
        "redirect_uri": settings.LINE_WORKS_REDIRECT_URI,
    }

    try:
        res = requests.post(token_url, data=payload, timeout=10)
        res.raise_for_status()
        tokens = res.json()
        id_token = tokens.get('id_token')

        if not id_token:
            raise ValueError("No id_token received")

        decoded = jwt.decode(id_token, options={"verify_signature": False})

        # ドメイン検証
        email = decoded.get('email', '')
        allowed_domain = getattr(settings, 'LINE_WORKS_DOMAIN', 'shin-on1981')

        if email and email.endswith(f"@{allowed_domain}") and not email.endswith(".com"):
            email = f"{email}.com"

        # ユーザー情報の取得・作成
        sub = decoded.get('sub')  # LINE WORKS User ID (UUID)
        email = decoded.get('email', '')

        # 追加情報の取得 (Users API を使用)
        # 以前の調査で UUID (sub) は 403 (Scope不足)、email は 404 だったため、
        # user.read スコープを付与した状態で再度 UUID を使用します
        bot_service = LineBotService()
        lw_user_data = bot_service.get_user_info(sub)

        if not lw_user_data:
            logger.warning(f"Failed to fetch additional info for sub={sub}, email={email} from Users API")
        else:
            logger.info(f"Successfully fetched info for sub={sub}")

        family_name = ""
        given_name = ""
        phonetic_family = ""
        phonetic_given = ""
        phone = ""

        # 取得できた情報でマッピング
        if lw_user_data:
            # 氏名情報
            name_info = lw_user_data.get('userName', {})
            family_name = name_info.get('lastName', '')
            given_name = name_info.get('firstName', '')
            phonetic_family = normalize_phonetic(name_info.get('phoneticLastName', ''))
            phonetic_given = normalize_phonetic(name_info.get('phoneticFirstName', ''))

            full_name = f"{family_name} {given_name}".strip() or name_info.get('fullName') or decoded.get('name')
            phone = lw_user_data.get('telephone') or lw_user_data.get('cellPhone') or ''
            email = lw_user_data.get('privateEmail') or lw_user_data.get('email') or email
        else:
            family_name = decoded.get('family_name', '')
            given_name = decoded.get('given_name', '')
            full_name = f"{family_name} {given_name}".strip() or decoded.get('name') or decoded.get('email') or 'Guest'

        user, created = User.objects.get_or_create(
            username=sub,
            defaults={
                'email': email,
                'first_name': full_name,
            }
        )

        # Profile情報の同期
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.family_name = family_name
        profile.given_name = given_name
        profile.phonetic_family_name = phonetic_family
        profile.phonetic_given_name = phonetic_given
        profile.phone_number = phone
        profile.email = email
        profile.save()

        if not created:
            if full_name and user.first_name != full_name:
                user.first_name = full_name
                user.save()

        # OTPフロー開始
        return initiate_otp_flow(request, user)

    except Exception as e:
        logger.error(f"SSO Callback Error: {e}", exc_info=True)
        return render(request, 'login.html', {'error': 'ログイン処理中にエラーが発生しました。'})


@login_required
def get_my_profile(request):
    """ログインユーザーのプロフィール情報を返すAPI"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    data = {
        'family_name': profile.family_name,
        'given_name': profile.given_name,
        'phonetic_family_name': profile.phonetic_family_name,
        'phonetic_given_name': profile.phonetic_given_name,
        'full_name': profile.full_name,
        'full_kana': profile.full_kana,
        'phone_number': profile.phone_number,
        'email': profile.email,
        'role': profile.role,
    }
    return JsonResponse({'status': 'success', 'data': data})


def initiate_otp_flow(request, user):
    """OTPを生成・送信し、認証画面へリダイレクト"""
    # Profile確保
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # ロック確認
    if profile.otp_locked_until and profile.otp_locked_until > timezone.now():
        remaining = int((profile.otp_locked_until - timezone.now()).total_seconds() / 60) + 1
        return render(request, 'login.html', {'error': f'試行回数が上限に達しました。{remaining}分後に再度お試しください。'})

    # OTP生成 (6桁)
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
    profile.otp_code = make_password(otp)
    profile.otp_expires_at = timezone.now() + timedelta(minutes=10)
    profile.otp_attempts = 0
    profile.save()

    # LINE WORKS Botで送信
    # 1-on-1メッセージ用のエンドポイントを使用する
    lw_id = user.email
    if lw_id and lw_id.endswith('.com'):
        allowed_domain = getattr(settings, 'LINE_WORKS_DOMAIN', 'shin-on1981')
        if f'@{allowed_domain}.com' in lw_id:
            lw_id = lw_id.replace('.com', '')

    bot_service = LineBotService()

    # OTPを3桁ずつに整形 (例: 123 456)
    formatted_otp = f"{otp[:3]} {otp[3:]}"
    msg = f"{formatted_otp}\n\n【RF Finder】ログイン認証コード\n有効期限: 10分"

    success = bot_service.send_user_message(lw_id, msg)
    if not success:
        logger.error(f"Failed to send OTP to {lw_id}")
        if not settings.DEBUG:
            return render(request, 'login.html', {'error': '認証コードの送信に失敗しました。'})

    # セッションにユーザーIDを一時保存
    request.session['otp_user_id'] = user.id
    return redirect('accounts:otp_verify')


def otp_verify(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:login')

    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return redirect('accounts:login')

    if request.method == 'POST':
        code = request.POST.get('code')

        # ロック確認
        if profile.otp_locked_until and profile.otp_locked_until > timezone.now():
            return render(request, 'otp_verify.html', {'error': 'アカウントがロックされています。'})

        # 有効期限確認
        if not profile.otp_expires_at or profile.otp_expires_at < timezone.now():
            return render(request, 'otp_verify.html', {'error': '有効期限が切れています。再送してください。'})

        # コード検証
        if code and check_password(code, profile.otp_code):
            # 認証成功
            profile.otp_code = ''
            profile.otp_attempts = 0
            profile.save()

            login(request, user)
            del request.session['otp_user_id']
            return redirect('facilities:index')
        else:
            # 認証失敗
            profile.otp_attempts += 1
            if profile.otp_attempts >= 5:
                profile.otp_locked_until = timezone.now() + timedelta(minutes=10)
                profile.otp_attempts = 0
                profile.save()
                return render(request, 'otp_verify.html', {'error': '試行回数が上限に達したため、10分間ロックされました。'})

            profile.save()
            return render(request, 'otp_verify.html', {'error': f'コードが正しくありません（残り{5 - profile.otp_attempts}回）。'})

    return render(request, 'otp_verify.html')


def otp_resend(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:login')

    try:
        user = User.objects.get(id=user_id)
        return initiate_otp_flow(request, user)
    except User.DoesNotExist:
        return redirect('accounts:login')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')
