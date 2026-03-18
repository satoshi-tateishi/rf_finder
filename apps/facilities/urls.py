from django.urls import path

from . import views

app_name = 'facilities'

urlpatterns = [
    path('search/', views.facility_search, name='search'),
    path('<int:facility_id>/', views.facility_detail, name='detail'),
]
