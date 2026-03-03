from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Q, When
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from apps.adjustments.utils import api_error, api_success

from .models import Facility, WirelessEquipment
from .services import calculate_available_frequencies


@login_required(login_url='accounts:login')
@never_cache
def index(request):
    """メイン画面（検索・視覚化）を表示"""
    # ユーザー指定の順序: SR2050 (上) -> EM 3732 N (中) -> EM 3732 L (下)
    devices = WirelessEquipment.objects.annotate(
        custom_order=Case(
            When(model_name__icontains='SR2050', then=0),
            When(Q(model_name__icontains='3732') & Q(model_name__icontains='N'), then=1),
            When(Q(model_name__icontains='3732') & Q(model_name__icontains='L'), then=2),
            default=3,
        )
    ).order_by('custom_order', 'model_name')
    return render(
        request,
        'index.html',
        {
            'devices': devices,
            'portal_url': settings.PORTAL_URL,
        },
    )


@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
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
                'category': facility.category,
                'applied_area': facility.applied_area,
            },
            'available_channels': available_channels,
        }
    )
