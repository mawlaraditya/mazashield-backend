from django.urls import path
from accounts.views import ProfileView, ChangePasswordView

urlpatterns = [
    path('profile', ProfileView.as_view(), name='profile'),                        # PBI-5
    path('profile/change-password', ChangePasswordView.as_view(), name='change-password'),  # PBI-6
]
