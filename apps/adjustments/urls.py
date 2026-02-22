from django.urls import path

from . import views

app_name = 'adjustments'

urlpatterns = [
    path('preview-pdf/', views.preview_pdf, name='preview_pdf'),
    path('preview-excel/', views.preview_excel, name='preview_excel'),
    path('send-email/', views.send_email, name='send_email'),
    path('test-send-text-message/', views.test_send_text_message, name='test_send_text_message'),
    path('test-send-pdf-message/', views.test_send_pdf_message, name='test_send_pdf_message'),
    path('log-woff-channel-id-result/', views.log_woff_channel_id_result, name='log_woff_channel_id_result'),
]
