import django_filters
from .models import Ternak, Daging, Invest

class TernakFilter(django_filters.FilterSet):
    nama = django_filters.CharFilter(lookup_expr='icontains')
    jenis = django_filters.CharFilter(lookup_expr='icontains')
    status_ternak = django_filters.CharFilter(lookup_expr='exact')
    
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
    
    min_harga = django_filters.NumberFilter(field_name="harga_per_kg", lookup_expr='gte')
    max_harga = django_filters.NumberFilter(field_name="harga_per_kg", lookup_expr='lte')

    class Meta:
        model = Daging
        fields = ['nama', 'bagian', 'status_daging']


class InvestFilter(django_filters.FilterSet):
    """Filter untuk Invest Ternak"""
    nama_paket = django_filters.CharFilter(lookup_expr='icontains')
    jenis = django_filters.CharFilter(lookup_expr='icontains')
    status_investernak = django_filters.CharFilter(lookup_expr='exact')
    
    # Range filters
    min_harga_sapi = django_filters.NumberFilter(field_name="harga_sapi", lookup_expr='gte')
    max_harga_sapi = django_filters.NumberFilter(field_name="harga_sapi", lookup_expr='lte')
    min_harga_jual = django_filters.NumberFilter(field_name="harga_jual", lookup_expr='gte')
    max_harga_jual = django_filters.NumberFilter(field_name="harga_jual", lookup_expr='lte')
    min_berat = django_filters.NumberFilter(field_name="berat", lookup_expr='gte')
    max_berat = django_filters.NumberFilter(field_name="berat", lookup_expr='lte')
    min_durasi = django_filters.NumberFilter(field_name="durasi_hari", lookup_expr='gte')
    max_durasi = django_filters.NumberFilter(field_name="durasi_hari", lookup_expr='lte')

    class Meta:
        model = Invest
        fields = ['nama_paket', 'jenis', 'status_investernak', 'id_invest']