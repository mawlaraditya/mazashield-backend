from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderMazdafarmViewSet, OrderMazdagingViewSet

router = DefaultRouter()
router.register(r'order/mazdafarm', OrderMazdafarmViewSet, basename='order-mazdafarm')
router.register(r'order/mazdaging', OrderMazdagingViewSet, basename='order-mazdaging')

urlpatterns = [
    # ── Mazdafarm Orders ────────────────────────────────────────────────────
    # PBI-23 POST /api/sales/order/mazdafarm/          → Create Order
    # PBI-25 GET  /api/sales/order/mazdafarm/          → Read Internal (List & Filter)
    
    # ── Mazdaging Orders ────────────────────────────────────────────────────
    # PBI-27 POST /api/sales/order/mazdaging/          → Create Order Daging
    # PBI-29 GET  /api/sales/order/mazdaging/          → Read Internal (List & Filter)
    
    path('', include(router.urls)),
]
