from django.urls import path
from accounts.views import RegisterView, LoginView, LogoutView

urlpatterns = [
    path('register', RegisterView.as_view(), name='auth-register'),   # PBI-1
    path('login', LoginView.as_view(), name='auth-login'),             # PBI-2
    path('logout', LogoutView.as_view(), name='auth-logout'),          # PBI-3
]
