from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.get_my_profile, name='me'),
    path('audit-logs/', views.list_audit_logs, name='list_audit_logs'),
    path('dropbox/login/', views.dropbox_login, name='dropbox_login'),
    path('dropbox/callback/', views.dropbox_callback, name='dropbox_callback'),
    path('dropbox/backup/', views.run_db_backup, name='run_db_backup'),
    path('dropbox/backups/', views.list_backups, name='list_backups'),
    path('dropbox/restore/', views.restore_db, name='restore_db'),
]
