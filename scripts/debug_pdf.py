import os
import sys
import django

# Django環境のセットアップ
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.adjustments.services import generate_adjustment_pdf
from apps.accounts.models import Member

def run():
    # サンプルデータ作成 (PDFサンプルに合わせる)
    test_data = {
        "app_type": "new",
        "user": {
            "name": "立石 智史",
            "kana": "たていし さとし",
            "tel": "090-2051-5474",
            "email": "s-tateishi@shin-on1981.com"
        },
        "event": {
            "name": "パルコ劇場",
            "comment": "※変更内容（局数、日時、現地使用者、使用場所、使用チャンネルなど）・キャンセルの旨・その他、伝達事項をご記入下さい。"
        },
        "facilities": [
            {
                "name": "パルコ劇場",
                "postal_code": "150-0042",
                "prefecture": "東京都",
                "address": "渋谷区宇田川町15-1",
                "category": "屋内",
                "applied_area": "8F パルコ劇場",
                "start_date": "2026-02-19",
                "end_date": "2026-02-19",
                "start_time": "09:00",
                "end_time": "22:00",
                "selectedChannels": [13, 14, 48, 49, 50]
            }
        ],
        "extra_53ch": "○",
        "mic_counts": {
            "analog_rm": {"10mw": "2"},
            "analog_53ch": {"rm_10mw": "1"},
            "digital_rm": {"10mw": "4"}
        }
    }

    member = Member.objects.first()
    pdf_buffer = generate_adjustment_pdf(test_data, member)
    
    output_path = os.path.join('media', 'debug_pdf', 'latest.pdf')
    with open(output_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    print(f"PDF generated at: {output_path}")

if __name__ == "__main__":
    run()
