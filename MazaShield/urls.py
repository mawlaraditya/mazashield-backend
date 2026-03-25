from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth & Accounts ──────────────────────────────────────────────────────
    path('api/auth/', include('accounts.urls.auth_urls')),
    path('api/', include('accounts.urls.profile_urls')),
    path('api/admin/', include('accounts.urls.admin_urls')),

    # ── Catalogs & Sales ──────────────────────────────────────────────────────
    path('api/sales/', include('catalogs.urls.internal_urls')),
    path('api/', include('catalogs.urls.public_urls')),
]

