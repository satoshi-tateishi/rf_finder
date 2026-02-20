from django import forms

class UserInfoForm(forms.Form):
    name = forms.CharField(max_length=255, required=False)
    kana = forms.CharField(max_length=255, required=False)
    tel = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)

class EventInfoForm(forms.Form):
    name = forms.CharField(max_length=50, required=True)
    comment = forms.CharField(max_length=165, required=False)

class AdjustmentRequestForm(forms.Form):
    app_type = forms.ChoiceField(choices=[('new', '新規'), ('change', '変更'), ('delete', '削除')], required=True)
    extra_53ch = forms.CharField(max_length=1, required=False)
    # Note: Nested data like 'facilities' and 'mic_counts' will be validated manually 
    # or via custom clean methods since Django Forms aren't ideal for deep nested JSON.
