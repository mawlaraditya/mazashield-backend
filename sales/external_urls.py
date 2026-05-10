from django.urls import path
from sales.views import OrderInvestExternalView, LaporanInvestasiCustomerView

urlpatterns = [
    # PBI-34: Read Order Investernak (External / Customer)
    path('invest/', OrderInvestExternalView.as_view(), name='order-invest-external'),

    # PBI-38: Read Laporan Hasil Investasi (Customer)
    path('invest/<int:id_pesanan>/laporan/', LaporanInvestasiCustomerView.as_view(), name='laporan-invest-customer'),
]
