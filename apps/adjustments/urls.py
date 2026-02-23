from django.urls import path

from . import views

app_name = 'adjustments'

urlpatterns = [
    path('preview-pdf/', views.preview_pdf, name='preview_pdf'),
    path('preview-excel/', views.preview_excel, name='preview_excel'),
    path('send-email/', views.send_email, name='send_email'),
    path('export-wsm/', views.export_wsm, name='export_wsm'),
]
