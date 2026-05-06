from django.urls import path
from .views import PaymentVerifyView, FinancialDashboardView

urlpatterns = [
    path('payment/<int:payment_id>/verify', PaymentVerifyView.as_view(), name='payment-verify'),
    # PBI-40: Financial Dashboard
    path('dashboard/', FinancialDashboardView.as_view(), name='financial-dashboard'),
]
