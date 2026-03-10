from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth & Accounts ──────────────────────────────────────────────────────
    path('api/auth/', include('accounts.urls.auth_urls')),
    path('api/', include('accounts.urls.profile_urls')),
    path('api/admin/', include('accounts.urls.admin_urls')),

    # ── Catalogs & Sales ──────────────────────────────────────────────────────
    path('api/sales/', include('catalogs.urls.internal_urls')),
    path('api/catalogs/', include('catalogs.urls.public_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
