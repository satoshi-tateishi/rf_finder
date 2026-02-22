import base64
import hashlib
import hmac

from django.conf import settings
from django.db.models import Case, Q, When
from django.shortcuts import render

from apps.adjustments.utils import api_error, api_success

from .models import Facility, WirelessEquipment
from .services import calculate_available_frequencies


def verify_woff_signature(request):
    """
    WOFFのリダイレクト検証を行う。
    """
    woff_id = settings.WOFF_ID
    secret_key = settings.WOFF_SECRET_KEY
    
    if not woff_id or not secret_key:
        return True # 設定がない場合はスキップ (開発用)

    timestamp = request.GET.get('timestamp')
    nonce = request.GET.get('nonce')
    signature = request.GET.get('signature')

    if not all([timestamp, nonce, signature]):
        return False

    # {woffId}{timestamp}{nonce} を HMAC-SHA256 で署名
    data = f"{woff_id}{timestamp}{nonce}"
    hmac_obj = hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    # Base64 URL エンコード (末尾のパディングを削除)
    expected = base64.urlsafe_b64encode(hmac_obj.digest()).decode('utf-8').rstrip('=')
    
    return hmac.compare_digest(expected, signature)


def index(request):
    """メイン画面（検索・視覚化）を表示"""
    # WOFFリダイレクト検証 (URLパラメータがある場合のみ実行)
    is_woff = 'signature' in request.GET
    woff_valid = False
    if is_woff:
        woff_valid = verify_woff_signature(request)

    # ユーザー指定の順序: SR2050 (上) -> EM 3732 N (中) -> EM 3732 L (下)
    devices = WirelessEquipment.objects.annotate(
        custom_order=Case(
            When(model_name__icontains='SR2050', then=0),
            When(Q(model_name__icontains='3732') & Q(model_name__icontains='N'), then=1),
            When(Q(model_name__icontains='3732') & Q(model_name__icontains='L'), then=2),
            default=3,
        )
    ).order_by('custom_order', 'model_name')
    return render(request, 'index.html', {
        'devices': devices,
        'woff_id': settings.WOFF_ID,
        'woff_valid': woff_valid,
        'is_woff': is_woff,
    })


def facility_search(request):
    """施設を名称で検索するAPI"""
    q = request.GET.get('q', '')
    if len(q) < 2:
        return api_success({'results': []})

    facilities = Facility.objects.filter(name__icontains=q)[:20]
    results = [
        {
            'id': f.id,
            'name': f.name,
            'address': f.address,
            'prefecture': f.prefecture,
            'applied_area': f.applied_area,
            'category': f.category,
            'postal_code': f.postal_code,
        }
        for f in facilities
    ]
    return api_success({'results': results})


def facility_detail(request, facility_id):
    """施設ごとの利用可能周波数リストを返すAPI"""
    try:
        facility = Facility.objects.get(pk=facility_id)
    except Facility.DoesNotExist:
        return api_error('Facility not found', status=404)

    available_channels = calculate_available_frequencies(facility)

    return api_success(
        {
            'facility': {
                'id': facility.id,
                'name': facility.name,
                'address': facility.address,
                'postal_code': facility.postal_code,
            },
            'available_channels': available_channels,
        }
    )
