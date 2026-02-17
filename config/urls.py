from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.facilities.urls')),
    path('api/facilities/', include('apps.facilities.urls')),
]
