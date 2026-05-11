from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth & Accounts ──────────────────────────────────────────────────────
    path('api/auth/', include('accounts.urls.auth_urls')),
    path('api/', include('accounts.urls.profile_urls')),
    path('api/admin/', include('accounts.urls.admin_urls')),

    # ── Catalogs & Sales & Finance ────────────────────────────────────────────
    path('api/sales/', include('catalogs.urls.internal_urls')),
    path('api/sales/', include('sales.urls')),
    path('api/finance/', include('sales.finance_urls')),
    path('api/', include('catalogs.urls.public_urls')),

      # ── PBI-34: External Invest Order (Customer read-only) ────────────────────
    # GET /api/order/invest/ → Customer's own invest orders
    # GET /api/order/invest/<id>/laporan/ → Customer reads their investment report (PBI-38)
    path('api/order/', include('sales.external_urls')),
]

