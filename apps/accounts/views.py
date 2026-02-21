import json
import requests
from django.views.decorators.csrf import csrf_exempt
from .models import WoffUser
from apps.adjustments.utils import api_error, api_success

@csrf_exempt
def get_user_profile(request):
    """
    LINE WORKS API v2 を使用して詳細なユーザー情報を取得するプロキシビュー。
    """
    if request.method != 'POST':
        return api_error('Method not allowed', status=405)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        access_token = data.get('accessToken')
        
        if not user_id or not access_token:
            return api_error('Missing userId or accessToken')
        
        # LINE WORKS API v2 エンドポイント (Official)
        url = f"https://www.worksapis.com/v1.0/users/{user_id}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            
            WoffUser.objects.update_or_create(
                user_id=user_id,
                defaults={
                    'name': f"{user_data.get('userName', {}).get('lastName', '')} {user_data.get('userName', {}).get('firstName', '')}".strip() or user_data.get('nickName', ''),
                    'email': user_data.get('privateEmail') or user_data.get('email', ''),
                    'phone': user_data.get('telephone') or user_data.get('cellPhone') or ''
                }
            )
            
            return api_success(user_data)
        else:
            # ログ出力を強化
            error_msg = f"[LINE WORKS API ERROR] Status: {response.status_code}, Response: {response.text}"
            print(error_msg)
            return api_error(f"LINE WORKS API Error: {response.status_code}", status=response.status_code, errors={'api_response': response.text})
            
    except Exception as e:
        print(f"[ERROR in get_user_profile] {e}")
        return api_error(str(e), status=500)
