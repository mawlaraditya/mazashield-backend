from django.urls import path
from .views import PaymentVerifyView

urlpatterns = [
    path('payment/<int:payment_id>/verify', PaymentVerifyView.as_view(), name='payment-verify'),
]
