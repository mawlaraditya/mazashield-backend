import django_filters
from .models import Ternak, Daging

class TernakFilter(django_filters.FilterSet):
    nama = django_filters.CharFilter(lookup_expr='icontains')
    jenis = django_filters.CharFilter(field_name='jenis', lookup_expr='icontains')
    status_ternak = django_filters.CharFilter(lookup_expr='exact')
    
    # Range filters for PBI 11 & 12
    min_harga = django_filters.NumberFilter(field_name="harga", lookup_expr='gte')
    max_harga = django_filters.NumberFilter(field_name="harga", lookup_expr='lte')
    min_berat = django_filters.NumberFilter(field_name="berat", lookup_expr='gte')
    max_berat = django_filters.NumberFilter(field_name="berat", lookup_expr='lte')

    class Meta:
        model = Ternak
        fields = ['nama', 'jenis', 'status_ternak', 'id_ternak']


class DagingFilter(django_filters.FilterSet):
    nama = django_filters.CharFilter(lookup_expr='icontains')
    bagian = django_filters.CharFilter(lookup_expr='icontains')
    status_daging = django_filters.CharFilter(lookup_expr='exact')
    
    # Range filters for PBI 16 & 17
    min_harga = django_filters.NumberFilter(field_name="harga_per_kg", lookup_expr='gte')
    max_harga = django_filters.NumberFilter(field_name="harga_per_kg", lookup_expr='lte')

    class Meta:
        model = Daging
        fields = ['nama', 'bagian', 'status_daging']