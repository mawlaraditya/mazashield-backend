import django_filters
from .models import Ternak

class TernakFilter(django_filters.FilterSet):
    nama = django_filters.CharFilter(lookup_expr='icontains')
    jenis = django_filters.CharFilter(lookup_expr='icontains')
    status_ternak = django_filters.CharFilter(lookup_expr='exact')
    id_ternak = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ternak
        fields = ['nama', 'jenis', 'status_ternak', 'id_ternak']


