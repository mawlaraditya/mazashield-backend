from django.urls import path
from catalogs.views import (
    TernakInternalListCreateView, TernakInternalDetailView,
    DagingInternalListCreateView, DagingInternalDetailView,
    InvestInternalListCreateView, InvestInternalDetailView,
)

urlpatterns = [
    # ── Mazdafarm Internal ────────────────────────────────────────────────────
    path('mazdafarm', TernakInternalListCreateView.as_view(), name='ternak-internal-list'),

    path('mazdafarm/<int:pk>', TernakInternalDetailView.as_view(), name='ternak-internal-detail'),

    # ── Mazdaging Internal ────────────────────────────────────────────────────
    path('mazdaging', DagingInternalListCreateView.as_view(), name='daging-internal-list'),
    path('mazdaging/<int:pk>', DagingInternalDetailView.as_view(), name='daging-internal-detail'),

    # ── Invest Ternak Internal ────────────────────────────────────────────────────
    path('invest', InvestInternalListCreateView.as_view(), name='invest-internal-list'),
    path('invest/<int:pk>', InvestInternalDetailView.as_view(), name='invest-internal-detail'),
]