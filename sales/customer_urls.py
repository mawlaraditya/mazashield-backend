from django.urls import path
from .views import CustomerOrderMazdafarmView, CustomerOrderMazdagingView

urlpatterns = [
    # PBI-External-1: Read Order Mazdafarm (Customer)
    # GET /api/order/mazdafarm/         → list pesanan milik customer yang login
    # GET /api/order/mazdafarm/<pk>/    → detail pesanan
    path('order/mazdafarm/', CustomerOrderMazdafarmView.as_view(), name='customer-order-mazdafarm-list'),
    path('order/mazdafarm/<int:pk>/', CustomerOrderMazdafarmView.as_view(), name='customer-order-mazdafarm-detail'),

    # PBI-External-2: Read Order Mazdaging (Customer)
    # GET /api/order/mazdaging/         → list order milik customer yang login
    # GET /api/order/mazdaging/<pk>/    → detail order
    path('order/mazdaging/', CustomerOrderMazdagingView.as_view(), name='customer-order-mazdaging-list'),
    path('order/mazdaging/<int:pk>/', CustomerOrderMazdagingView.as_view(), name='customer-order-mazdaging-detail'),
]
