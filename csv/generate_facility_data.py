import pandas as pd
import unicodedata
import re
from pathlib import Path

# --- 設定 ---
CSV_DIR = Path("csv")
ZIP_CSV = CSV_DIR / "utf_ken_all.csv"
LOCATIONS_CSV = CSV_DIR / "locations.csv"
OUTPUT_CSV = CSV_DIR / "locations_with_zip.csv"

def normalize_address(text):
    """住所の正規化（マッチング精度向上のため）"""
    if not isinstance(text, str): return ""
    # Unicode正規化 (NFKC)
    text = unicodedata.normalize('NFKC', text)
    # 漢数字を英数字に変換
    kanji_map = str.maketrans('一二三四五六七八九〇', '1234567890')
    text = text.translate(kanji_map)
    # 住所の区切りを正規化
    text = re.sub(r'([0-9]+)丁目', r'\1-', text)
    text = re.sub(r'([0-9]+)番[地丁]?', r'\1-', text)
    text = re.sub(r'([0-9]+)号', r'\1', text)
    text = text.replace(' ', '').replace('　', '')
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def main():
    print("--- 施設データCSV生成開始 ---")

    # 1. 郵便番号データの読み込み
    print(f"読み込み中: {ZIP_CSV}...")
    # utf_ken_all.csv の形式: 2:郵便番号, 6:都道府県, 7:市区町村, 8:町域
    try:
        zip_df = pd.read_csv(ZIP_CSV, header=None, dtype={2: str}, encoding='utf-8')
    except Exception as e:
        print(f"エラー: {ZIP_CSV} の読み込みに失敗しました。{e}")
        return

    zip_df = zip_df[[2, 6, 7, 8]]
    zip_df.columns = ['zip', 'pref', 'city', 'town']
    zip_df['town'] = zip_df['town'].replace('以下に掲載がない場合', '')

    print("郵便番号マスターを構築中...")
    zip_lookup = []
    for _, row in zip_df.iterrows():
        full_addr = normalize_address(str(row['pref']) + str(row['city']) + str(row['town']))
        if full_addr:
            zip_lookup.append((full_addr, row['zip']))
    
    # 住所が長い順にソート（より詳細な一致を優先）
    zip_lookup.sort(key=lambda x: len(x[0]), reverse=True)

    # 2. 施設データの読み込み
    print(f"読み込み中: {LOCATIONS_CSV}...")
    try:
        f_df = pd.read_csv(LOCATIONS_CSV)
    except Exception as e:
        print(f"エラー: {LOCATIONS_CSV} の読み込みに失敗しました。{e}")
        return

    print(f"{len(f_df)} 件の施設の住所照合を開始...")

    def find_zip_code(row):
        # 都道府県名と住所を結合して照合
        raw_addr = str(row.get('都道府県名', '')) + str(row.get('住所', ''))
        norm_target = normalize_address(raw_addr)
        if not norm_target: return ""
        
        for addr_key, zip_code in zip_lookup:
            if addr_key in norm_target:
                return zip_code
        return ""

    # 照合の実行
    f_df['郵便番号'] = f_df.apply(find_zip_code, axis=1)
    
    # 郵便番号の書式を整える (000-0000)
    f_df['郵便番号'] = f_df['郵便番号'].apply(
        lambda x: f"{x[:3]}-{x[3:]}" if len(str(x)) == 7 else x
    )

    # 3. カラムの調整 (update_db.py のロジックを継承)
    # 53CHを強制的に '○' に設定（元のCSVにない場合を考慮）
    f_df['53CH'] = '○'

    # '郵便番号' を先頭列に移動
    cols = f_df.columns.tolist()
    if '郵便番号' in cols:
        cols.insert(0, cols.pop(cols.index('郵便番号')))
        f_df = f_df[cols]

    # 4. 保存
    f_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    success_count = (f_df['郵便番号'] != "").sum()
    print(f"✅ 完了！ 保存先: {OUTPUT_CSV}")
    print(f"照合成功: {success_count} / {len(f_df)} 件")

if __name__ == "__main__":
    main()
