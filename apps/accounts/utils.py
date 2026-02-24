import unicodedata


def katakana_to_hiragana(text):
    """
    カタカナをひらがなに変換する。
    """
    if not text:
        return ""

    # 全角カタカナをひらがなに変換 (Unicode の差分 0x60 を引く)
    # カタカナ: 0x30A1 - 0x30F6
    # ひらがな: 0x3041 - 0x3096
    result = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)

    return "".join(result)

def normalize_phonetic(text):
    """
    ふりがなをひらがなに正規化し、余分な空白を除去する。
    """
    if not text:
        return ""
    # NFKC正規化 (全角英数を半角にするなど)
    text = unicodedata.normalize('NFKC', text)
    return katakana_to_hiragana(text).strip()
