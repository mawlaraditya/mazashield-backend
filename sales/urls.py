from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderMazdafarmViewSet, OrderMazdagingViewSet, OrderInvestViewSet,
    PaymentUpdateView, PaymentVerifyView, RiwayatPembayaranViewSet
)

router = DefaultRouter()
router.register(r'order/mazdafarm', OrderMazdafarmViewSet, basename='order-mazdafarm')
router.register(r'order/mazdaging', OrderMazdagingViewSet, basename='order-mazdaging')
router.register(r'order/invest', OrderInvestViewSet, basename='order-invest')
router.register(r'payment/history', RiwayatPembayaranViewSet, basename='payment-history')

urlpatterns = [
    # ── Mazdafarm Orders ─────────────────────────────
    # POST /api/sales/order/mazdafarm/ → Create Order
    # GET  /api/sales/order/mazdafarm/ → Read Internal (List & Filter)

    # ── Mazdaging Orders ─────────────────────────────
    # POST /api/sales/order/mazdaging/ → Create Order Daging
    # GET  /api/sales/order/mazdaging/ → Read Internal (List & Filter)

    # ── Invest Orders ─────────────────────────────────
    # POST /api/sales/order/invest/ → Create Order Invest
    # GET  /api/sales/order/invest/ → Read Internal (List & Filter)
    # PUT  /api/sales/order/invest/{pk}/ → Update Status

    path('payment/<int:id_pesanan>/update', PaymentUpdateView.as_view(), name='payment-update'),

      # ── PBI-37: Laporan Investasi (Marketing/SuperAdmin) ──────────────────────
    # GET  /api/sales/laporan-invest/<id>/ → Read laporan (auto-create if missing)
    # POST /api/sales/laporan-invest/<id>/berat/ → Add weekly weight entry
    # PUT  /api/sales/laporan-invest/<id>/akhir/ → Save final calculation
    path('laporan-invest/<int:id_pesanan>/', LaporanInvestasiView.as_view(), name='laporan-invest-read'),
    path('laporan-invest/<int:id_pesanan>/berat/', LaporanInvestasiBeratView.as_view(), name='laporan-invest-berat'),
    path('laporan-invest/<int:id_pesanan>/akhir/', LaporanInvestasiAkhirView.as_view(), name='laporan-invest-akhir'),

    # ── PBI-39: Laporan Penjualan (Marketing/SuperAdmin) ─────────────────────
    # GET /api/sales/laporan-penjualan/?start_date=&end_date=&jenis_layanan=&page=&limit=
    path('laporan-penjualan/', LaporanPenjualanView.as_view(), name='laporan-penjualan'),

    path('', include(router.urls)),

    # ── PBI-39: Laporan Penjualan (Marketing/SuperAdmin) ─────────────────────
    # GET /api/sales/laporan-penjualan/?start_date=&end_date=&jenis_layanan=&page=&limit=
    path('laporan-penjualan/', LaporanPenjualanView.as_view(), name='laporan-penjualan'),

]