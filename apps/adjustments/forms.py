from django import forms

class UserInfoForm(forms.Form):
    name = forms.CharField(max_length=255, required=True, error_messages={'required': '氏名を入力してください'})
    kana = forms.CharField(max_length=255, required=True, error_messages={'required': 'ふりがなを入力してください'})
    tel = forms.CharField(max_length=20, required=True, error_messages={'required': '電話番号を入力してください'})
    email = forms.EmailField(required=True, error_messages={'required': 'メールアドレスを入力してください'})

class EventInfoForm(forms.Form):
    name = forms.CharField(max_length=50, required=True, error_messages={'required': '催事名を入力してください'})
    comment = forms.CharField(max_length=165, required=False)

class AdjustmentRequestForm(forms.Form):
    app_type = forms.ChoiceField(choices=[('new', '新規'), ('change', '変更'), ('delete', '削除')], required=True)
    extra_53ch = forms.CharField(max_length=1, required=False)
    
    # エラー紐付け用のダミーフィールド
    facilities = forms.CharField(required=False)
    mic_counts = forms.CharField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        data = self.data
        
        # 1. 施設リストのバリデーション
        facilities = data.get('facilities', [])
        if not facilities:
            self.add_error('facilities', '施設を1つ以上選択してください')
        
        for i, f in enumerate(facilities):
            if not f.get('start_date') or not f.get('end_date') or not f.get('start_time') or not f.get('end_time'):
                self.add_error('facilities', f'施設 {i+1} の日程・時間をすべて入力してください')

        # 2. 使用マイク数のバリデーション
        mc = data.get('mic_counts', {})
        
        def sum_mics(d):
            s = 0
            if isinstance(d, dict):
                for v in d.values():
                    s += sum_mics(v)
            elif isinstance(d, (int, str)) and str(d).isdigit():
                s += int(d)
            return s
            
        total_mics = sum_mics(mc)
        if total_mics == 0 and not mc.get('12g_lmh'):
            self.add_error('mic_counts', '使用マイク数を少なくとも1箇所入力してください')

        return cleaned_data
