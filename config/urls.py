from django.contrib import admin
from django.urls import include, path

from apps.facilities import views as facility_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', facility_views.index, name='index'),               # メイン画面（SPA）
    path('api/facilities/', include('apps.facilities.urls')),   # 施設検索・詳細 API
    path('api/adjustments/', include('apps.adjustments.urls')), # 調整届 API
    path('auth/', include('apps.accounts.urls')),               # 認証・アカウント
]
