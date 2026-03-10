from django.urls import path
from catalogs.views import (
    TernakInternalListCreateView, TernakInternalDetailView,
    # DagingInternalListCreateView, DagingInternalDetailView,
)

urlpatterns = [
    # ── Mazdafarm Internal ────────────────────────────────────────────────────
    # PBI-8  POST  /api/sales/mazdafarm    → Create
    # PBI-11 GET   /api/sales/mazdafarm    → Read Internal
    path('mazdafarm', TernakInternalListCreateView.as_view(), name='ternak-internal-list'),

    # PBI-9  PUT    /api/sales/mazdafarm/<id>  → Update
    # PBI-10 DELETE /api/sales/mazdafarm/<id>  → Soft Delete
    path('mazdafarm/<int:pk>', TernakInternalDetailView.as_view(), name='ternak-internal-detail'),

    # ── Mazdaging Internal ────────────────────────────────────────────────────
    # PBI-13 POST  /api/sales/mazdaging    → Create
    # PBI-16 GET   /api/sales/mazdaging    → Read Internal
    # path('mazdaging', DagingInternalListCreateView.as_view(), name='daging-internal-list'),

    # PBI-14 PUT    /api/sales/mazdaging/<id>  → Update
    # PBI-15 DELETE /api/sales/mazdaging/<id>  → Soft Delete
    # path('mazdaging/<int:pk>', DagingInternalDetailView.as_view(), name='daging-internal-detail')
]