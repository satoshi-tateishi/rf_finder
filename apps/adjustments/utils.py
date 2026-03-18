import json
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .constants import APP_TYPE_MAP, APP_TYPE_NEW


def format_channels(channels):
    if not channels:
        return ''
    sorted_channels = sorted(list(set(map(int, channels))))
    result = []
    i = 0
    while i < len(sorted_channels):
        start = sorted_channels[i]
        end = start
        while i + 1 < len(sorted_channels) and sorted_channels[i + 1] == end + 1:
            end = sorted_channels[i + 1]
            i += 1
        if end - start >= 2:
            result.append(f'{start}-{end}')
        else:
            for val in range(start, end + 1):
                result.append(str(val))
        i += 1
    return ', '.join(result)


def api_success(data=None):
    return JsonResponse({'status': 'success', 'data': data}, json_dumps_params={'ensure_ascii': False})


def api_error(message, status=400, errors=None):
    payload = {'status': 'error', 'message': message}
    if errors:
        payload['errors'] = errors
    return JsonResponse(payload, status=status, json_dumps_params={'ensure_ascii': False})


def json_api_view(validate=False):
    """
    POSTリクエストの解析とバリデーションを共通化するデコレータ。
    認証チェック・メソッドチェック・JSONパース・バリデーションを一括処理する。
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='accounts:login')
        def _wrapped_view(request, *args, **kwargs):
            if request.method != 'POST':
                return api_error('Method not allowed', status=405)

            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return api_error('Invalid JSON', status=400)

            if validate:
                # 循環参照を避けるため実行時にインポート
                from .views import validate_adjustment_data

                is_valid, errors = validate_adjustment_data(data)
                if not is_valid:
                    return api_error('Validation failed', errors=errors)

            return view_func(request, data, *args, **kwargs)

        return _wrapped_view

    return decorator


def get_adjustment_filename(data, extension='pdf'):
    """
    運用連絡票のファイル名を生成する。
    形式: 運用連絡票_{区分}_{催事名}_{運用開始日}.{extension}
    """
    app_type_raw = data.get('app_type', APP_TYPE_NEW)
    app_type_jp = APP_TYPE_MAP.get(app_type_raw, '新規')

    event_name = data.get('event', {}).get('name', '無題の催事')

    facilities = data.get('facilities', [])
    start_date = facilities[0].get('start_date', '') if facilities else ''
    # 日付からハイフンを除去 (YYYY-MM-DD -> YYYYMMDD)
    date_str = start_date.replace('-', '') if start_date else '未定'

    # ファイル名に使用できない文字をサニタイズ（簡易）
    safe_event_name = ''.join([c for c in event_name if c not in r'\/:*?"<>|']).strip()

    return f'運用連絡票_{app_type_jp}_{safe_event_name}_{date_str}.{extension}'
