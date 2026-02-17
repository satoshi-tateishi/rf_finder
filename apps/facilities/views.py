from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Facility, WirelessEquipment
from .services import calculate_available_frequencies

def index(request):
    """メイン画面（検索・視覚化）を表示"""
    devices = WirelessEquipment.objects.all().order_by('model_name')
    return render(request, 'index.html', {'devices': devices})

def facility_search(request):
    """施設を名称で検索するAPI"""
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse({'results': []})
    
    facilities = Facility.objects.filter(name__icontains=q)[:20]
    results = [
        {
            'id': f.id,
            'name': f.name,
            'address': f.address,
            'prefecture': f.prefecture,
            'applied_area': f.applied_area,
            'category': f.category
        } for f in facilities
    ]
    return JsonResponse({'results': results})

def facility_detail(request, facility_id):
    """施設ごとの利用可能周波数リストを返すAPI"""
    try:
        facility = Facility.objects.get(pk=facility_id)
    except Facility.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
        
    available_channels = calculate_available_frequencies(facility)
    
    return JsonResponse({
        'facility': {
            'id': facility.id,
            'name': facility.name,
            'address': facility.address,
        },
        'available_channels': available_channels
    })
