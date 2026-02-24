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
    path('dropbox/login/', views.dropbox_login, name='dropbox_login'),
    path('dropbox/callback/', views.dropbox_callback, name='dropbox_callback'),
    path('dropbox/backup/', views.run_db_backup, name='run_db_backup'),
]
