from rest_framework import serializers
from .models import Pesanan, OrderItem, Pembayaran, PesananDaging, OrderItemDaging, PembayaranDaging
from accounts.models import User
from catalogs.models import Ternak, Daging

class OrderItemSerializer(serializers.ModelSerializer):
    id_ternak = serializers.CharField(source='ternak.id_ternak')
    nama = serializers.CharField(source='ternak.nama')
    berat = serializers.DecimalField(source='ternak.berat', max_digits=10, decimal_places=2)
    
    class Meta:
        model = OrderItem
        fields = ['id_ternak', 'nama', 'berat', 'harga']

class PembayaranSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pembayaran
        fields = ['tagihan', 'menunggu_persetujuan', 'sudah_dibayar']

class PesananSerializer(serializers.ModelSerializer):
    """
    PBI-23,25: Serializer untuk Read & Detail Pesanan Mazdafarm
    """
    data_customer = serializers.SerializerMethodField()
    daftar_ternak = OrderItemSerializer(source='items', many=True, read_only=True)
    total_item = serializers.SerializerMethodField()
    tagihan = serializers.DecimalField(source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True)
    menunggu_persetujuan = serializers.DecimalField(source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True)
    sudah_dibayar = serializers.DecimalField(source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True)
    id_pesanan = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Pesanan
        fields = [
            'id_pesanan', 'data_customer', 'daftar_ternak', 'total_item', 
            'tagihan', 'menunggu_persetujuan', 'sudah_dibayar', 
            'status_pesanan', 'catatan', 'created_at', 'updated_at'
        ]
    
    def get_data_customer(self, obj):
        return {
            'nama': obj.customer.nama,
            'no_telp': obj.customer.nomor_telepon,
            'email': obj.customer.email
        }
    
    def get_total_item(self, obj):
        return obj.items.count()

class OrderCreateSerializer(serializers.Serializer):
    """
    PBI-23: Serializer untuk Create Pesanan Mazdafarm
    """
    id_customer = serializers.IntegerField()
    daftar_id_ternak = serializers.ListField(child=serializers.CharField())
    catatan = serializers.CharField(required=False, allow_blank=True)

    def validate_id_customer(self, value):
        if not User.objects.filter(id=value).exists():
            # The requirement says return 404, but standard DRF validation returns 400.
            # I will handle 404 in the view to strictly follow PBI.
            return value
        return value

class OrderUpdateSerializer(serializers.ModelSerializer):
    """
    PBI-24: Serializer untuk Update Status Pesanan Mazdafarm
    """
    class Meta:
        model = Pesanan
        fields = ['status_pesanan', 'catatan']
    
    def validate_status_pesanan(self, value):
        if value not in ['Diproses', 'Selesai', 'Dibatalkan']:
            raise serializers.ValidationError("Status pesanan tidak valid.")
        return value
