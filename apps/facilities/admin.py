from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Case, When, Q
from import_export.admin import ImportExportModelAdmin
from .models import Facility, TVChannelStatus, WirelessEquipment
from .resources import FacilityResource, WirelessEquipmentResource, TVChannelStatusResource

class PrefectureJisFilter(admin.SimpleListFilter):
    title = '都道府県'
    parameter_name = 'prefecture'

    # JISコード順の都道府県リスト
    PREFECTURES_JIS = [
        '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
        '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
        '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
        '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
        '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
        '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
        '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
    ]

    def lookups(self, request, model_admin):
        # データベースに存在する都道府県のみをJIS順で抽出
        existing_prefs = set(Facility.objects.values_list('prefecture', flat=True).distinct())
        return [(p, p) for p in self.PREFECTURES_JIS if p in existing_prefs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(prefecture=self.value())
        return queryset

@admin.register(Facility)
class FacilityAdmin(ImportExportModelAdmin):
    resource_class = FacilityResource
    list_display = ('get_facility_info',)
    list_display_links = ('get_facility_info',)
    ordering = ('id',)
    search_fields = ('name', 'address', 'external_id')
    list_filter = (PrefectureJisFilter, 'category')
    
    readonly_fields = ('facility_info_card', 'channel_grid')
    fieldsets = (
        ('基本情報', {
            'fields': ('facility_info_card',),
        }),
        ('使用可能チャンネル', {
            'fields': ('channel_grid',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        js = ('js/admin_row_click.js',)

    @admin.display(description='施設情報')
    def get_facility_info(self, obj):
        css = format_html(
            '<style>'
            '.field-get_facility_info a {{ text-decoration: none !important; color: inherit !important; display: block; padding: 8px; margin: -8px; }}'
            '.field-get_facility_info:hover {{ background-color: #eff6ff !important; cursor: pointer; }}'
            '</style>'
        )
        
        category_badge = format_html(
            '<span style="background: #f3f4f6; color: #4b5563; font-size: 10px; padding: 2px 6px; border-radius: 4px; border: 1px solid #e5e7eb; margin-left: 5px; vertical-align: middle;">{}</span>',
            obj.category
        ) if obj.category else ""
        
        area_badge = format_html(
            '<span style="background: #eff6ff; color: #2563eb; font-size: 10px; padding: 2px 6px; border-radius: 4px; border: 1px solid #dbeafe; margin-left: 5px; vertical-align: middle;">{}</span>',
            obj.applied_area
        ) if obj.applied_area else ""
        
        zip_display = format_html('<span style="margin-right: 5px;">〒{}</span>', obj.external_id) if obj.external_id else ""
        
        return format_html(
            '{}'
            '<div>'
            '<div style="margin-bottom: 4px;">'
            '<span style="font-weight: bold; color: #1f2937; font-size: 14px;">{}</span>'
            '{}{}'
            '</div>'
            '<div style="font-size: 11px; color: #6b7280;">{}{}{}</div>'
            '</div>',
            css,
            obj.name,
            category_badge,
            area_badge,
            zip_display,
            obj.prefecture,
            obj.address
        )

    @admin.display(description='')
    def facility_info_card(self, obj):
        from django.utils.safestring import mark_safe
        
        category_badge = format_html(
            '<span style="background: #f3f4f6; color: #4b5563; font-size: 10px; padding: 2px 8px; border-radius: 4px; border: 1px solid #e5e7eb; margin-left: 8px; vertical-align: middle; font-weight: normal;">{}</span>',
            obj.category
        ) if obj.category else ""
        
        area_badge = format_html(
            '<span style="background: #eff6ff; color: #2563eb; font-size: 10px; padding: 2px 8px; border-radius: 4px; border: 1px solid #dbeafe; margin-left: 8px; vertical-align: middle; font-weight: normal;">{}</span>',
            obj.applied_area
        ) if obj.applied_area else ""
        
        zip_display = format_html('<span style="margin-right: 5px;">〒{}</span>', obj.external_id) if obj.external_id else ""
        
        css = """
        <style>
            /* ページタイトルの書き換えと重複する施設名の非表示 */
            #content > h1 { font-size: 0 !important; margin-bottom: 20px !important; }
            #content > h1::before { content: "施設詳細" !important; font-size: 20px !important; visibility: visible !important; }
            #content > h2 { display: none !important; }
            
            /* ラベルの非表示と全幅表示設定 */
            .field-facility_info_card label, .field-channel_grid label { display: none !important; }
            .field-facility_info_card .readonly, .field-channel_grid .readonly { width: 100% !important; margin-left: 0 !important; padding: 0 !important; }
        </style>
        """
        
        card_html = format_html(
            '<div style="background: #fff; border-radius: 8px; border: 1px solid #e5e7eb; border-left: 5px solid #10b981; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); max-width: 900px; margin-top: 5px;">'
            '<div style="margin-bottom: 10px;">'
            '<span style="font-weight: bold; color: #1f2937; font-size: 18px;">{}</span>'
            '{}{}'
            '</div>'
            '<div style="font-size: 13px; color: #6b7280;">{}{}{}</div>'
            '</div>',
            obj.name,
            category_badge,
            area_badge,
            zip_display,
            obj.prefecture,
            obj.address
        )
        return mark_safe(css + card_html)

    @admin.display(description='')
    def channel_grid(self, obj):
        from .services import calculate_available_frequencies
        from django.utils.safestring import mark_safe
        
        # ユーザー指定の順序でデバイスを取得
        devices = WirelessEquipment.objects.annotate(
            custom_order=Case(
                When(model_name__icontains='SR2050', then=0),
                When(Q(model_name__icontains='3732') & Q(model_name__icontains='N'), then=1),
                When(Q(model_name__icontains='3732') & Q(model_name__icontains='L'), then=2),
                default=3
            )
        ).order_by('custom_order', 'model_name')
        
        available_channels = calculate_available_frequencies(obj)
        available_map = {c['channel']: c for c in available_channels}
        
        def get_device_color(name):
            if 'SR2050' in name: return '#f97316'
            if '3732' in name and 'N' in name: return '#3b82f6'
            if '3732' in name and 'L' in name: return '#22c55e'
            return '#94a3b8'

        css = """
        <style>
            .admin-ch-card { background: #fff; border-radius: 8px; border: 1px solid #e5e7eb; border-left: 5px solid #3b82f6; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); max-width: 900px; margin-top: 5px; }
            .admin-ch-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(64px, 1fr)); gap: 6px; margin-top: 15px; }
            .admin-ch-btn { aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.8rem; position: relative; border-radius: 4px; border: 1px solid #d1d5db; background-color: white; color: #374151; }
            .admin-ch-btn.disabled { background-color: #f3f4f6; color: #d1d5db; border-color: #e5e7eb; }
            .admin-device-indicators { position: absolute; bottom: 4px; left: 4px; right: 4px; display: flex; flex-direction: column; gap: 2px; }
            .admin-device-bar { height: 3px; border-radius: 1px; }
            .admin-gb-indicator { position: absolute; top: 0; height: 3px; background-color: #fbbf24; opacity: 0.8; }
            .admin-legend { display: flex; flex-wrap: wrap; gap: 15px; font-size: 11px; padding-bottom: 15px; border-bottom: 1px solid #f3f4f6; }
            .admin-legend-item { display: flex; align-items: center; gap: 6px; color: #6b7280; font-weight: bold; }
            .admin-legend-dot { width: 10px; height: 10px; border-radius: 50%; }
            .admin-legend-bar { width: 16px; height: 4px; border-radius: 1px; }
        </style>
        """
        
        legend_html = ['<div class="admin-legend">']
        for d in devices:
            legend_html.append(
                format_html('<div class="admin-legend-item"><span class="admin-legend-dot" style="background:{}"></span> {}</div>',
                            get_device_color(d.model_name), d.model_name)
            )
        legend_html.append('<div class="admin-legend-item"><span class="admin-legend-bar" style="background:#fbbf24;"></span> GB (1MHz)</div>')
        legend_html.append('<div class="admin-legend-item"><span class="admin-legend-bar" style="background:#f3f4f6; border:1px solid #d1d5db;"></span> N/A</div>')
        legend_html.append('</div>')
        
        grid_html = ['<div class="admin-ch-grid">']
        for ch in range(13, 54):
            ch_data = available_map.get(ch)
            btn_class = "admin-ch-btn" if ch_data else "admin-ch-btn disabled"
            grid_html.append(format_html('<div class="{}"><span>{}</span>', btn_class, ch))
            
            if ch_data:
                base_start = ch_data['base_start']
                ch_width = 4000 if ch == 53 else 6000
                
                if ch_data['gb_lower'] > 0:
                    width = (ch_data['gb_lower'] / ch_width) * 100
                    grid_html.append(format_html('<div class="admin-gb-indicator" style="left:0; width:{}%;"></div>', width))
                if ch_data['gb_upper'] > 0:
                    width = (ch_data['gb_upper'] / ch_width) * 100
                    grid_html.append(format_html('<div class="admin-gb-indicator" style="right:0; width:{}%;"></div>', width))
                
                grid_html.append('<div class="admin-device-indicators">')
                for d in devices:
                    overlap_min = max(d.min_frequency, base_start)
                    overlap_max = min(d.max_frequency, base_start + ch_width)
                    
                    if overlap_min < overlap_max:
                        width = ((overlap_max - overlap_min) / ch_width) * 100
                        margin = ((overlap_min - base_start) / ch_width) * 100
                        grid_html.append(format_html('<div class="admin-device-bar" style="background:{}; width:{}%; margin-left:{}%;"></div>',
                                                     get_device_color(d.model_name), width, margin))
                    else:
                        grid_html.append('<div class="admin-device-bar" style="background:transparent; width:100%;"></div>')
                grid_html.append('</div>')
            
            grid_html.append('</div>')
        grid_html.append('</div>')
        
        card_html = f'<div class="admin-ch-card">{"".join(legend_html)}{"".join(grid_html)}</div>'
        
        return mark_safe(css + card_html)

@admin.register(WirelessEquipment)
class WirelessEquipmentAdmin(ImportExportModelAdmin):
    resource_class = WirelessEquipmentResource
    list_display = ('model_name', 'manufacturer', 'min_frequency', 'max_frequency')
    search_fields = ('model_name', 'manufacturer')
