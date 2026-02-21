from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('woff/profile/', views.get_user_profile, name='woff_profile'),
]
