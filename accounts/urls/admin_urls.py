from django.urls import path
from accounts.views import AdminRegisterView, AdminUserListView, AdminUserDeleteView, AdminUserUpdateView, AdminUserExportView

urlpatterns = [
    path('users', AdminRegisterView.as_view(), name='admin-register'),     # PBI-4 POST
    path('users/list', AdminUserListView.as_view(), name='admin-users'),   # PBI-4 GET
    path('users/export', AdminUserExportView.as_view(), name='admin-export-users'),
    path('users/<int:pk>', AdminUserUpdateView.as_view(), name='admin-update-user'), # GET details or PUT update
    path('users/<int:pk>/delete', AdminUserDeleteView.as_view(), name='admin-delete-user'),  # PBI-7
]
