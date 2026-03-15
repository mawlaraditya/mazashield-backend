from django.urls import path
from catalogs.views import (
    TernakPublicListView,
    DagingPublicListView,
    InvestPublicListView,
)

urlpatterns = [
    # PBI-12 GET /api/mazdafarm   → Public catalog Mazdafarm
    path('mazdafarm', TernakPublicListView.as_view(), name='ternak-public-list'),

    # PBI-17 GET /api/mazdaging   → Public catalog Mazdaging
    path('mazdaging', DagingPublicListView.as_view(), name='daging-public-list'),

    # GET /api/invest   → Public catalog Invest Ternak
    path('invest', InvestPublicListView.as_view(), name='invest-public-list'),
]