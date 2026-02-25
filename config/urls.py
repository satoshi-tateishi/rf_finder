from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.facilities.urls')),
    path('api/facilities/', include('apps.facilities.urls')),
    path('api/adjustments/', include('apps.adjustments.urls')),
    # path('api/accounts/', include('apps.accounts.urls')), # Removed to avoid duplicate namespace
    path('auth/', include('apps.accounts.urls')),  # Web画面用
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
