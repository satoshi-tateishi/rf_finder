import io
import openpyxl
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.units import mm
from django.conf import settings
import os

def format_channels(channels):
    if not channels: return ""
    sorted_channels = sorted(list(set(map(int, channels))))
    result = []
    i = 0
    while i < len(sorted_channels):
        start = sorted_channels[i]
        end = start
        while i + 1 < len(sorted_channels) and sorted_channels[i+1] == end + 1:
            end = sorted_channels[i+1]
            i += 1
        if end - start >= 2: result.append(f"{start}-{end}")
        else:
            for val in range(start, end + 1): result.append(str(val))
        i += 1
    return ", ".join(result)

def generate_adjustment_excel(data, member=None):
    """
    Excelテンプレートにデータを書き込んで返す。
    結合セルの場合は左上のセル（マスターセル）に値を書き込む必要がある。
    """
    template_path = os.path.join(settings.BASE_DIR, 'Excel', 'master.xlsx')
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    # 1. 基本情報
    # 申請区分
    app_type = data.get('app_type', 'new')
    type_text = '新規' if app_type == 'new' else '変更' if app_type == 'change' else '削除'
    ws['D4'] = type_text # D4:E8 merged

    if member:
        ws['M4'] = member.member_id_1 # Corrected to M4
        ws['P4'] = member.member_id_2
        ws['W4'] = member.name
        ws['M6'] = member.department or ""
        ws['W6'] = member.manager_name
        ws['M8'] = member.phone
        ws['W8'] = member.email

    # 2. 現地使用者
    user = data.get('user', {})
    ws['O13'] = f"{user.get('name')}（{user.get('kana')}）"
    ws['L15'] = user.get('tel')
    ws['W15'] = user.get('email')

    # 3. 催事情報
    event = data.get('event', {})
    ws['H18'] = event.get('name')
    
    # コメント欄の整形 (55文字毎に改行、既存の改行は無視)
    comment = (event.get('comment') or "").replace('\n', '').replace('\r', '')
    ws['E20'] = comment[0:55]
    ws['B21'] = comment[55:110]
    ws['B22'] = comment[110:165]

    # 4. 使用マイク数
    mc = data.get('mic_counts', {})
    ws['K27'] = mc.get('analog_rm', {}).get('10mw')
    ws['R27'] = mc.get('analog_53ch', {}).get('rm_10mw')
    ws['K28'] = mc.get('analog_em', {}).get('10mw')
    ws['R28'] = mc.get('analog_53ch', {}).get('em_10mw')
    
    ws['K29'] = mc.get('digital_rm', {}).get('10mw')
    ws['M29'] = mc.get('digital_rm', {}).get('20mw')
    ws['O29'] = mc.get('digital_rm', {}).get('50mw')
    ws['R29'] = mc.get('digital_53ch', {}).get('10mw')
    ws['U29'] = mc.get('digital_53ch', {}).get('20mw')
    ws['W29'] = mc.get('digital_53ch', {}).get('50mw')
    
    # 1.2G
    ws['Z29'] = mc.get('digital_12g', {}).get('10mw')
    ws['AB29'] = mc.get('digital_12g', {}).get('20mw')
    ws['AD29'] = mc.get('digital_12g', {}).get('50mw')
    ws['AI27'] = mc.get('12g_lmh')

    # 53ch併用
    if data.get('extra_53ch') == '○':
        ws['AF31'] = '○' # Corrected to AF31

    # 5. 施設リスト
    for i, f in enumerate(data.get('facilities', [])):
        if i >= 4: break
        base_row = 34 + (i * 12)
        
        ws.cell(row=base_row, column=5).value = f.get('start_date')  # E
        ws.cell(row=base_row, column=14).value = f.get('end_date')   # N (Corrected)
        ws.cell(row=base_row, column=22).value = f.get('start_time') # V (Corrected)
        ws.cell(row=base_row, column=27).value = f.get('end_time')   # AA
        
        ws.cell(row=base_row + 2, column=10).value = f.get('postal_code') # J
        ws.cell(row=base_row + 2, column=18).value = f"{f.get('prefecture')}{f.get('address')}" # R
        
        ws.cell(row=base_row + 4, column=12).value = f.get('category') # L
        ws.cell(row=base_row + 4, column=18).value = f.get('name')     # R
        
        ws.cell(row=base_row + 6, column=15).value = f.get('applied_area') # O (Corrected)
        ws.cell(row=base_row + 8, column=15).value = format_channels(f.get('selectedChannels', [])) # O (Corrected)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def generate_adjustment_pdf(data, member=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansJP-Regular.ttf')
    font_name = 'NotoSansJP' if os.path.exists(font_path) else 'Helvetica'
    if font_name == 'NotoSansJP':
        pdfmetrics.registerFont(TTFont('NotoSansJP', font_path))

    def draw_cell(x, y, w, h, text, bg=None, align='center', f_size=7, text_color=colors.black, stroke=True):
        if bg:
            p.setFillColor(bg)
            p.rect(x*mm, y*mm, w*mm, h*mm, fill=1)
        if stroke:
            p.setStrokeColor(colors.black)
            p.setLineWidth(0.15*mm)
            p.rect(x*mm, y*mm, w*mm, h*mm)
        p.setFillColor(text_color)
        p.setFont(font_name, f_size)
        if text:
            if align == 'center':
                p.drawCentredString((x + w/2)*mm, (y + h/2)*mm - f_size/3, text)
            elif align == 'right':
                p.drawRightString((x + w - 2)*mm, (y + h/2)*mm - f_size/3, text)
            else:
                p.drawString((x + 2)*mm, (y + h/2)*mm - f_size/3, text)

    def draw_vertical_text(x, y, text, f_size=8):
        p.setFont(font_name, f_size)
        p.setFillColor(colors.black)
        for i, char in enumerate(text):
            p.drawCentredString(x*mm, (y - i*4)*mm, char)

    # 1. Header
    p.setFont(font_name, 18); p.drawString(15*mm, 282*mm, "運用連絡票")
    p.setFont(font_name, 9); p.drawString(48*mm, 282.5*mm, "(一社)特定ラジオマイク運用調整機構")
    p.setFont(font_name, 8); p.drawRightString(195*mm, 287*mm, f"提出日: {datetime.now().strftime('%Y/%m/%d')}")
    p.setFont(font_name, 8); p.setFillColor(colors.blue); p.drawRightString(195*mm, 282*mm, "E-mail: rm-unyo@radiomic.org")
    p.setFillColor(colors.black)

    # 2. Member Info Section
    draw_cell(15, 255, 10, 25, "", bg=colors.HexColor('#F5F5F5'))
    draw_vertical_text(20, 272, "会員情報", f_size=7)
    
    app_type = data.get('app_type', 'new')
    draw_cell(25, 255, 25, 25, "") 
    p.setFont(font_name, 12); p.drawCentredString(37.5*mm, 265*mm, "新規" if app_type == 'new' else "変更" if app_type == 'change' else "削除")
    
    draw_cell(50, 272, 25, 8, "会員番号", bg=colors.HexColor('#F5F5F5'))
    if member:
        draw_cell(75, 272, 15, 8, member.member_id_1, f_size=9)
        draw_cell(90, 272, 10, 8, "－")
        draw_cell(100, 272, 20, 8, member.member_id_2, f_size=9)
        draw_cell(120, 272, 20, 8, "会員名", bg=colors.HexColor('#F5F5F5'))
        draw_cell(140, 272, 55, 8, member.name, align='left', f_size=8)
        draw_cell(50, 264, 25, 8, "部署", bg=colors.HexColor('#F5F5F5'))
        draw_cell(75, 264, 45, 8, member.department or "", align='left', f_size=8)
        draw_cell(120, 264, 20, 8, "運用担当者", bg=colors.HexColor('#F5F5F5'))
        draw_cell(140, 264, 55, 8, member.manager_name, align='left', f_size=8)
        draw_cell(50, 256, 25, 8, "Tel", bg=colors.HexColor('#F5F5F5'))
        draw_cell(75, 256, 45, 8, member.phone, align='left', f_size=8)
        draw_cell(120, 256, 20, 8, "E-mail", bg=colors.HexColor('#F5F5F5'))
        draw_cell(140, 256, 55, 8, member.email, align='left', f_size=7)

    # 3. User Info
    draw_cell(15, 240, 35, 15, "現地使用者", bg=colors.HexColor('#F5F5F5'), f_size=9)
    user = data.get('user', {})
    draw_cell(50, 247.5, 70, 7.5, f"氏名（ふりがな）： {user.get('name')}（{user.get('kana')}）", align='left', f_size=8)
    draw_cell(120, 247.5, 75, 7.5, f"E-mail： {user.get('email')}", align='left', f_size=7)
    draw_cell(50, 240, 70, 7.5, f"Tel： {user.get('tel')}", align='left', f_size=8)
    draw_cell(120, 240, 75, 7.5, "", align='left')

    # 4. Event & Comment
    draw_cell(15, 230, 35, 10, "催事名", bg=colors.red, text_color=colors.white, f_size=10)
    event = data.get('event', {})
    draw_cell(50, 230, 145, 10, event.get('name', ''), align='left', bg=colors.HexColor('#FFE4E1'), f_size=10)

    draw_cell(15, 210, 180, 20, "", align='left')
    p.setFont(font_name, 8); p.drawString(17*mm, 225*mm, "コメント：")
    p.setFont(font_name, 7); p.setFillColor(colors.blue)
    p.drawString(17*mm, 220*mm, event.get('comment', '')[:100])

    # 6. Mic counts
    tx, ty = 15, 185
    cw = [35, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15]
    rh = 8
    draw_cell(tx, ty, cw[0], rh*2, "使用マイク数", bg=colors.HexColor('#FFE4E1'), text_color=colors.red, f_size=8)
    draw_cell(tx + cw[0], ty + rh, sum(cw[1:4]), rh, "TV WS", f_size=8)
    draw_cell(tx + cw[0] + sum(cw[1:4]), ty + rh, sum(cw[4:7]), rh, "※710-714(53ch)", f_size=7)
    draw_cell(tx + cw[0] + sum(cw[1:7]), ty + rh, sum(cw[7:11]), rh, "1.2G(基本はLです。)", f_size=7)
    
    sub_h = ["送信出力(mW)", "10mW", "20mW", "50mW", "10mW", "20mW", "50mW", "10mW", "20mW", "50mW", "L,M,H"]
    for i, h_txt in enumerate(sub_h):
        draw_cell(tx + sum(cw[:i]), ty, cw[i], rh, h_txt, bg=colors.HexColor('#F5F5F5'), f_size=6)

    mc = data.get('mic_counts', {})
    rows = [
        ("アナログ RM", [mc.get('analog_rm',{}).get('10mw',''), "--", "--", mc.get('analog_53ch',{}).get('rm_10mw',''), "--", "--", "--", "--", "--", mc.get('12g_lmh','')]),
        ("〃 EM", [mc.get('analog_em',{}).get('10mw',''), "--", "--", mc.get('analog_53ch',{}).get('em_10mw',''), "--", "--", "--", "--", "--", None]),
        ("デジタル RM", [mc.get('digital_rm',{}).get('10mw',''), mc.get('digital_rm',{}).get('20mw',''), mc.get('digital_rm',{}).get('50mw',''), mc.get('digital_53ch',{}).get('10mw',''), mc.get('digital_53ch',{}).get('20mw',''), mc.get('digital_53ch',{}).get('50mw',''), mc.get('digital_12g',{}).get('10mw',''), mc.get('digital_12g',{}).get('20mw',''), mc.get('digital_12g',{}).get('50mw',''), ""])
    ]
    ry = ty - rh
    for r_idx, (label, vals) in enumerate(rows):
        draw_cell(tx, ry, cw[0], rh, label, bg=colors.HexColor('#F5F5F5'), align='left', f_size=7)
        for c_idx, val in enumerate(vals):
            if val is None: continue
            x_pos = tx + sum(cw[:c_idx+1])
            bg, txt, h_val = (colors.HexColor('#D3D3D3'), "", rh) if val == "--" else (None, str(val or ""), rh)
            if c_idx == 9: 
                if r_idx == 0: h_val, bg = rh*2, colors.HexColor('#FFE4E1')
                elif r_idx == 2: bg = colors.HexColor('#D3D3D3')
            draw_cell(x_pos, ry if c_idx != 9 or r_idx != 0 else ry-rh, cw[c_idx+1], h_val, txt, bg=bg)
        ry -= rh

    p.setStrokeColor(colors.black); p.setLineWidth(0.15*mm)
    p.rect(tx*mm, (ry - 5)*mm, (width/mm - 55)*mm, 6*mm)
    p.rect((width/mm - 40)*mm, (ry - 5)*mm, 25*mm, 6*mm)
    p.setFont(font_name, 5); p.setFillColor(colors.blue)
    p.drawString((tx+2)*mm, (ry-1)*mm, "TVWS の使用申請で、状況により「53ch」を併用する可能性がある場合：右枠に○印をご記入下さい。（注）使用マイク数はすべてTVWS枠に記入して下さい")
    p.setFont(font_name, 9); p.setFillColor(colors.black)
    if data.get('extra_53ch') == '○': p.drawCentredString((width/mm - 27.5)*mm, (ry-1)*mm, "○")

    fy = ry - 15
    for i, f in enumerate(data.get('facilities', [])):
        if i >= 4: break
        draw_cell(tx, fy, 10, 25, str(i+1), bg=colors.HexColor('#F5F5F5'))
        draw_cell(tx + 10, fy + 18, 100, 7, f"日付: {f.get('start_date')} 〜 {f.get('end_date')}", align='left', bg=colors.HexColor('#FFE4E1'), text_color=colors.red, f_size=8)
        draw_cell(tx + 110, fy + 18, 70, 7, f"時間: {f.get('start_time')} 〜 {f.get('end_time')}", align='left', bg=colors.HexColor('#FFE4E1'), text_color=colors.red, f_size=8)
        
        draw_cell(tx + 10, fy, 30, 18, "使用場所", bg=colors.HexColor('#F5F5F5'), f_size=8)
        draw_cell(tx + 40, fy + 12, 25, 6, f"〒 {f.get('postal_code')}", f_size=7)
        draw_cell(tx + 65, fy + 12, 115, 6, f"住所: {f.get('prefecture')}{f.get('address')}", align='left', f_size=7)
        draw_cell(tx + 40, fy + 6, 25, 6, f"屋内/屋外: {f.get('category')}", f_size=7)
        draw_cell(tx + 65, fy + 6, 115, 6, f"施設名: {f.get('name')}", align='left', f_size=8, text_color=colors.red)
        
        draw_cell(tx + 10, fy - 7, 30, 7, "使用TVチャンネル", bg=colors.HexColor('#F5F5F5'), f_size=7)
        draw_cell(tx + 40, fy - 7, 140, 7, format_channels(f.get('selectedChannels', [])), align='left', f_size=9, text_color=colors.red)
        fy -= 38

    p.showPage(); p.save(); buffer.seek(0)
    return buffer
