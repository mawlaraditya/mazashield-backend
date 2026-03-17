from django.contrib import admin
from .models import Ternak, Daging, Invest

@admin.register(Ternak)
class TernakAdmin(admin.ModelAdmin):
    list_display = ('id_ternak', 'nama', 'jenis', 'kelas', 'berat', 'status_ternak')
    list_filter = ('jenis', 'kelas', 'status_ternak')
    search_fields = ('id_ternak', 'nama')

@admin.register(Daging)
class DagingAdmin(admin.ModelAdmin):
    list_display = ('id_daging', 'nama', 'bagian', 'harga_per_kg', 'status_daging')
    list_filter = ('bagian', 'status_daging')
    search_fields = ('id_daging', 'nama')

@admin.register(Invest)
class InvestAdmin(admin.ModelAdmin):
    list_display = ('id_invest', 'nama_paket', 'jenis', 'roi_persen', 'status_investernak')
    list_filter = ('jenis', 'status_investernak')
    search_fields = ('id_invest', 'nama_paket')
