from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('lineworks/login/', views.lineworks_login, name='lineworks_login'),
    path('lineworks/callback/', views.lineworks_callback, name='lineworks_callback'),
    path('otp/verify/', views.otp_verify, name='otp_verify'),
    path('otp/resend/', views.otp_resend, name='otp_resend'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.get_my_profile, name='me'),
    path('audit-logs/', views.list_audit_logs, name='list_audit_logs'),
]
