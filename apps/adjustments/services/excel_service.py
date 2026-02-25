import io
import os

import openpyxl
from django.conf import settings
from django.utils import timezone

from ..constants import APP_TYPE_MAP
from ..utils import format_channels

# PDF出力時の余白設定 (cm単位)
PDF_MARGIN_TOP_CM = 1.0
PDF_MARGIN_BOTTOM_CM = 1.0
PDF_MARGIN_LEFT_CM = 0.6
PDF_MARGIN_RIGHT_CM = 0.6
PDF_MARGIN_HEADER_CM = 0.5
PDF_MARGIN_FOOTER_CM = 0.5

# 単位変換用定数 (1cm = 0.393701インチ)
CM_TO_INCH = 0.393701

# Excel セル座標定数
CELL_SUBMISSION_DATE = 'AD1'
CELL_APP_TYPE = 'D4'
CELL_MEMBER_ID_1 = 'M4'
CELL_MEMBER_ID_2 = 'P4'
CELL_MEMBER_NAME = 'W4'
CELL_MEMBER_DEPT = 'M6'
CELL_MEMBER_MANAGER = 'W6'
CELL_MEMBER_PHONE = 'M8'
CELL_MEMBER_EMAIL = 'W8'

CELL_USER_NAME = 'O13'
CELL_USER_TEL = 'L15'
CELL_USER_EMAIL = 'W15'

CELL_EVENT_NAME = 'H18'
CELL_EVENT_COMMENT_LINE1 = 'E20'
CELL_EVENT_COMMENT_LINE2 = 'B21'
CELL_EVENT_COMMENT_LINE3 = 'B22'

CELL_53CH_EXTRA = 'AF31'
CELL_12G_LMH = 'AF27'

# マイク数セル (Analog / Digital)
CELLS_MIC_COUNTS = {
    'analog_rm_10mw': 'K27',
    'analog_53ch_rm_10mw': 'R27',
    'analog_em_10mw': 'K28',
    'analog_53ch_em_10mw': 'R28',
    'digital_rm_10mw': 'K29',
    'digital_rm_20mw': 'M29',
    'digital_rm_50mw': 'O29',
    'digital_53ch_10mw': 'R29',
    'digital_53ch_20mw': 'U29',
    'digital_53ch_50mw': 'W29',
    'digital_12g_10mw': 'Z29',
    'digital_12g_20mw': 'AB29',
    'digital_12g_50mw': 'AD29',
}


def _write_common_info(ws, data, member, current_date, pad_func):
    """共通情報（申請者、催事、マイク数など）をシートに書き込む"""
    
    # 0. 提出日
    ws[CELL_SUBMISSION_DATE] = current_date

    # 1. 基本情報
    app_type = data.get('app_type', 'new')
    ws[CELL_APP_TYPE] = APP_TYPE_MAP.get(app_type, '新規')

    if member:
        ws[CELL_MEMBER_ID_1] = member.member_id_1 or ''
        ws[CELL_MEMBER_ID_2] = member.member_id_2 or ''
        ws[CELL_MEMBER_NAME] = pad_func(member.name)
        ws[CELL_MEMBER_DEPT] = pad_func(member.department)
        ws[CELL_MEMBER_MANAGER] = pad_func(member.manager_name)
        ws[CELL_MEMBER_PHONE] = pad_func(member.phone)
        ws[CELL_MEMBER_EMAIL] = pad_func(member.email)

    # 2. 現地使用者
    user = data.get('user') or {}
    user_display = f'{user.get("name", "")}（{user.get("kana", "")}）'
    ws[CELL_USER_NAME] = pad_func(user_display if user_display != '（）' else '')
    ws[CELL_USER_TEL] = pad_func(user.get('tel', ''))
    ws[CELL_USER_EMAIL] = pad_func(user.get('email', ''))

    # 3. 催事情報
    event = data.get('event') or {}
    ws[CELL_EVENT_NAME] = pad_func(event.get('name', ''))

    # 改行を半角スペースに置換して保持
    comment = (event.get('comment') or '').replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    ws[CELL_EVENT_COMMENT_LINE1] = pad_func(comment[0:55])
    ws[CELL_EVENT_COMMENT_LINE2] = pad_func(comment[55:110])
    ws[CELL_EVENT_COMMENT_LINE3] = pad_func(comment[110:165])

    # 4. 使用マイク数
    mc = data.get('mic_counts') or {}
    ws[CELLS_MIC_COUNTS['analog_rm_10mw']] = mc.get('analog_rm', {}).get('10mw', '')
    ws[CELLS_MIC_COUNTS['analog_53ch_rm_10mw']] = mc.get('analog_53ch', {}).get('rm_10mw', '')
    ws[CELLS_MIC_COUNTS['analog_em_10mw']] = mc.get('analog_em', {}).get('10mw', '')
    ws[CELLS_MIC_COUNTS['analog_53ch_em_10mw']] = mc.get('analog_53ch', {}).get('em_10mw', '')

    ws[CELLS_MIC_COUNTS['digital_rm_10mw']] = mc.get('digital_rm', {}).get('10mw', '')
    ws[CELLS_MIC_COUNTS['digital_rm_20mw']] = mc.get('digital_rm', {}).get('20mw', '')
    ws[CELLS_MIC_COUNTS['digital_rm_50mw']] = mc.get('digital_rm', {}).get('50mw', '')
    
    ws[CELLS_MIC_COUNTS['digital_53ch_10mw']] = mc.get('digital_53ch', {}).get('10mw', '')
    ws[CELLS_MIC_COUNTS['digital_53ch_20mw']] = mc.get('digital_53ch', {}).get('20mw', '')
    ws[CELLS_MIC_COUNTS['digital_53ch_50mw']] = mc.get('digital_53ch', {}).get('50mw', '')

    ws[CELLS_MIC_COUNTS['digital_12g_10mw']] = mc.get('digital_12g', {}).get('10mw', '')
    ws[CELLS_MIC_COUNTS['digital_12g_20mw']] = mc.get('digital_12g', {}).get('20mw', '')
    ws[CELLS_MIC_COUNTS['digital_12g_50mw']] = mc.get('digital_12g', {}).get('50mw', '')
    
    ws[CELL_12G_LMH] = mc.get('12g_lmh', '')

    if data.get('extra_53ch') == '○':
        ws[CELL_53CH_EXTRA] = '○'


def _write_facilities(ws, facilities_slice, pad_func):
    """施設リスト（最大4施設）をシートに書き込む"""
    for i, f in enumerate(facilities_slice):
        if not isinstance(f, dict):
            continue
            
        base_row = 34 + (i * 12)
        ws.cell(row=base_row, column=5).value = f.get('start_date', '')
        ws.cell(row=base_row, column=14).value = f.get('end_date', '')
        ws.cell(row=base_row, column=22).value = f.get('start_time', '')
        ws.cell(row=base_row, column=27).value = f.get('end_time', '')
        ws.cell(row=base_row + 2, column=10).value = pad_func(f.get('postal_code', ''))
        
        address_display = f'{f.get("prefecture", "")}{f.get("address", "")}'
        ws.cell(row=base_row + 2, column=18).value = pad_func(address_display)
        
        ws.cell(row=base_row + 4, column=12).value = pad_func(f.get('category', ''))
        ws.cell(row=base_row + 4, column=18).value = pad_func(f.get('name', ''))
        ws.cell(row=base_row + 6, column=15).value = pad_func(f.get('applied_area', ''))
        
        channels = f.get('selectedChannels') or []
        ws.cell(row=base_row + 8, column=15).value = pad_func(format_channels(channels))


def generate_adjustment_excel(data, member=None, for_pdf=False):
    """
    Excelテンプレートにデータを書き込んで返す。
    """
    template_path = os.path.join(settings.BASE_DIR, 'Excel', 'master.xlsx')
    if not os.path.exists(template_path):
        raise FileNotFoundError(f'Template not found at {template_path}')

    wb = openpyxl.load_workbook(template_path)

    # 施設データの型安全性を確保
    facilities = data.get('facilities') or []
    if not isinstance(facilities, list):
        facilities = []
    
    num_facilities = len(facilities)

    # 使用するシートを決定
    target_sheets = ['master_01']
    if num_facilities > 4:
        target_sheets.append('master_02')
    if num_facilities > 8:
        target_sheets.append('master_03')

    # 日本時間での日付取得
    current_date = timezone.localtime().strftime('%Y/%m/%d')

    def pad(val):
        if not val:
            return ''
        return f' {val}' if for_pdf else str(val)

    for sheet_idx, sheet_name in enumerate(target_sheets):
        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]

        # PDF出力用のページ設定 (余白設定)
        if for_pdf:
            ws.page_margins.top = PDF_MARGIN_TOP_CM * CM_TO_INCH
            ws.page_margins.bottom = PDF_MARGIN_BOTTOM_CM * CM_TO_INCH
            ws.page_margins.left = PDF_MARGIN_LEFT_CM * CM_TO_INCH
            ws.page_margins.right = PDF_MARGIN_RIGHT_CM * CM_TO_INCH
            ws.page_margins.header = PDF_MARGIN_HEADER_CM * CM_TO_INCH
            ws.page_margins.footer = PDF_MARGIN_FOOTER_CM * CM_TO_INCH
            # 印刷範囲を明示的に指定して変換を安定させる
            ws.print_area = 'A1:AJ80'

        # 共通情報の書き込み
        _write_common_info(ws, data, member, current_date, pad)

        # 施設情報の書き込み
        start_idx = sheet_idx * 4
        sheet_facilities = facilities[start_idx : start_idx + 4]
        _write_facilities(ws, sheet_facilities, pad)

    # 不要なシートを安全に削除
    for s in list(wb.sheetnames):
        if s not in target_sheets:
            del wb[s]

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
