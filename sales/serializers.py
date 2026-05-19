from rest_framework import serializers
from .models import (
    Pesanan, OrderItem, Pembayaran, 
    PesananDaging, OrderItemDaging, PembayaranDaging, 
    PesananInvest, OrderItemInvest, PembayaranInvest,
    RiwayatPembayaran, HistoriBerat, LaporanInvestasi
)
from accounts.models import User
from catalogs.models import Ternak, Daging, Invest

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

    log_pembayaran = serializers.SerializerMethodField()

    class Meta:
        model = Pesanan
        fields = [
            'id_pesanan', 'data_customer', 'daftar_ternak', 'total_item', 
            'tagihan', 'menunggu_persetujuan', 'sudah_dibayar', 
            'status_pesanan', 'catatan', 'created_at', 'updated_at', 'log_pembayaran'
        ]
    
    def get_log_pembayaran(self, obj):
        # Optimized: Use prefetched payment_logs
        riwayat = obj.payment_logs.all()
        return [
            {
                'id': r.id,
                'nominal_pembayaran': r.nominal_pembayaran,
                'bank_pengirim': r.bank_pengirim,
                'nomor_rekening_pengirim': r.nomor_rekening_pengirim,
                'nama_pengirim': r.nama_pengirim,
                'status': r.status,
                'catatan_verifikasi': r.catatan_verifikasi,
                'created_at': r.created_at,
                'created_by_name': r.created_by.nama if r.created_by else 'Sistem',
                'verified_by_name': r.verified_by.nama if r.verified_by else None,
            } for r in riwayat
        ]
    
    def get_data_customer(self, obj):
        return {
            'nama': obj.customer.nama,
            'no_telp': obj.customer.nomor_telepon,
            'email': obj.customer.email
        }
    
    def get_total_item(self, obj):
        # Optimized: Use prefetched items to avoid extra database query
        return len(obj.items.all())

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
        if value not in ['Processed', 'Completed', 'Cancelled']:
            raise serializers.ValidationError("Status pesanan tidak valid.")
        return value
    
# MAZDAGING SERIALIZERS
class OrderItemDagingSerializer(serializers.ModelSerializer):
    id_daging = serializers.CharField(source='daging.id_daging')
    nama = serializers.CharField(source='daging.nama')
    bagian = serializers.CharField(source='daging.bagian')
    
    class Meta:
        model = OrderItemDaging
        fields = ['id_daging', 'nama', 'bagian', 'berat_pesanan_kg', 'harga_per_kg', 'subtotal_item']

class PesananDagingSerializer(serializers.ModelSerializer):
    """
    PBI-27, PBI-29 (Anne): Serializer untuk Read & Detail Pesanan Mazdaging
    """
    data_customer = serializers.SerializerMethodField()
    daftar_item = OrderItemDagingSerializer(source='items', many=True, read_only=True)
    total_item = serializers.SerializerMethodField()
    tagihan = serializers.DecimalField(source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True)
    menunggu_persetujuan = serializers.DecimalField(source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True)
    sudah_dibayar = serializers.DecimalField(source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True)
    id_pesanan = serializers.IntegerField(source='id', read_only=True)

    log_pembayaran = serializers.SerializerMethodField()

    class Meta:
        model = PesananDaging
        fields = [
            'id_pesanan', 'data_customer', 'daftar_item', 'total_item', 
            'tagihan', 'menunggu_persetujuan', 'sudah_dibayar', 
            'status_pesanan', 'catatan', 'created_at', 'updated_at', 'log_pembayaran'
        ]
    
    def get_log_pembayaran(self, obj):
        # Optimized: Use prefetched payment_logs GenericRelation
        riwayat = obj.payment_logs.all()
        return [
            {
                'id': r.id,
                'nominal_pembayaran': r.nominal_pembayaran,
                'bank_pengirim': r.bank_pengirim,
                'nomor_rekening_pengirim': r.nomor_rekening_pengirim,
                'nama_pengirim': r.nama_pengirim,
                'status': r.status,
                'catatan_verifikasi': r.catatan_verifikasi,
                'created_at': r.created_at,
                'created_by_name': r.created_by.nama if r.created_by else 'Sistem',
                'verified_by_name': r.verified_by.nama if r.verified_by else None,
            } for r in riwayat
        ]
    
    def get_data_customer(self, obj):
        return {
            'nama': obj.customer.nama,
            'no_telp': obj.customer.nomor_telepon,
            'email': obj.customer.email
        }
    
    def get_total_item(self, obj):
        # Optimized: Use prefetched items to avoid extra database query
        return len(obj.items.all())

class OrderDagingCreateSerializer(serializers.Serializer):
    """
    PBI-27 (Anne): Serializer untuk Create Pesanan Mazdaging
    """
    id_customer = serializers.IntegerField()
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    catatan = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, value):
        for item in value:
            if 'id_daging' not in item or 'berat_pesanan_kg' not in item:
                raise serializers.ValidationError("Setiap item harus memuat id_daging dan berat_pesanan_kg.")
            if not isinstance(item['berat_pesanan_kg'], (int, float, str)):
                raise serializers.ValidationError("berat_pesanan_kg harus numerik.")
            try:
                weight = float(item['berat_pesanan_kg'])
                if weight <= 0:
                    raise serializers.ValidationError("berat_pesanan_kg harus lebih besar dari 0.")
            except ValueError:
                raise serializers.ValidationError("berat_pesanan_kg harus numerik.")
        return value


# ── INVEST ORDER SERIALIZERS ────────────────────────────────────────────────
class OrderItemInvestSerializer(serializers.ModelSerializer):
    id_invest = serializers.CharField(source='invest.id_invest')
    nama_paket = serializers.CharField(source='invest.nama_paket')
    jenis = serializers.CharField(source='invest.jenis')
    berat = serializers.DecimalField(source='invest.berat', max_digits=10, decimal_places=2, allow_null=True)
    harga_jual = serializers.DecimalField(source='invest.harga_jual', max_digits=15, decimal_places=2)
    roi_persen = serializers.DecimalField(source='invest.roi_persen', max_digits=10, decimal_places=2)
    status_investernak = serializers.CharField(source='invest.status_investernak')

    class Meta:
        model = OrderItemInvest
        fields = ['id_invest', 'nama_paket', 'jenis', 'berat', 'harga_sapi', 'harga_jual', 'roi_persen', 'status_investernak']


class PesananInvestSerializer(serializers.ModelSerializer):
    id_pesanan = serializers.IntegerField(source='id', read_only=True)
    data_customer = serializers.SerializerMethodField()
    daftar_invest = OrderItemInvestSerializer(source='items', many=True, read_only=True)
    total_item = serializers.SerializerMethodField()
    tagihan = serializers.DecimalField(source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True)
    menunggu_persetujuan = serializers.DecimalField(source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True)
    sudah_dibayar = serializers.DecimalField(source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True)

    log_pembayaran = serializers.SerializerMethodField()

    class Meta:
        model = PesananInvest
        fields = [
            'id_pesanan', 'data_customer', 'daftar_invest', 'total_item',
            'tagihan', 'menunggu_persetujuan', 'sudah_dibayar',
            'status_pesanan', 'catatan', 'created_at', 'updated_at', 'log_pembayaran'
        ]

    def get_log_pembayaran(self, obj):
        # Optimized: Use prefetched payment_logs GenericRelation
        riwayat = obj.payment_logs.all()
        return [
            {
                'id': r.id,
                'nominal_pembayaran': r.nominal_pembayaran,
                'bank_pengirim': r.bank_pengirim,
                'nomor_rekening_pengirim': r.nomor_rekening_pengirim,
                'nama_pengirim': r.nama_pengirim,
                'status': r.status,
                'catatan_verifikasi': r.catatan_verifikasi,
                'created_at': r.created_at,
                'created_by_name': r.created_by.nama if r.created_by else 'Sistem',
                'verified_by_name': r.verified_by.nama if r.verified_by else None,
            } for r in riwayat
        ]

    def get_data_customer(self, obj):
        return {
            'nama': obj.customer.nama,
            'no_telp': obj.customer.nomor_telepon,
            'email': obj.customer.email,
        }

    def get_total_item(self, obj):
        # Optimized: Use prefetched items to avoid extra database query
        return len(obj.items.all())


class OrderInvestCreateSerializer(serializers.Serializer):
    id_customer = serializers.IntegerField()
    items = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    catatan = serializers.CharField(required=False, allow_blank=True)


class OrderInvestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PesananInvest
        fields = ['status_pesanan', 'catatan']

    def validate_status_pesanan(self, value):
        if value not in ['Processed', 'Completed', 'Cancelled']:
            raise serializers.ValidationError("Status pesanan tidak valid.")
        return value

class RiwayatPembayaranSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    order_id = serializers.IntegerField(source='object_id', read_only=True)
    order_type = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.nama', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.nama', read_only=True)
    
    class Meta:
        model = RiwayatPembayaran
        fields = [
            'id', 'order_id', 'order_type', 'customer_name', 'nominal_pembayaran', 
            'bank_pengirim', 'nomor_rekening_pengirim', 'nama_pengirim', 'tanggal_transfer', 
            'waktu_transfer', 'catatan', 'status', 'created_at', 'created_by', 'created_by_name',
            'verified_at', 'verified_by', 'verified_by_name', 'catatan_verifikasi'
        ]
        read_only_fields = ['created_by', 'verified_at', 'verified_by', 'status']

    def get_customer_name(self, obj):
        if obj.content_object and hasattr(obj.content_object, 'customer'):
            return obj.content_object.customer.nama
        return None

    def get_order_type(self, obj):
        if obj.content_type:
            return obj.content_type.model
        return None


# ── CUSTOMER-FACING SERIALIZERS (Read-Only, External) ──────────────────────

class CustomerOrderItemMazdafarmSerializer(serializers.ModelSerializer):
    """
    PBI-External-1: Item ternak dalam pesanan untuk tampilan Customer.
    Memuat nama, berat, umur, harga, dan foto.
    """
    nama = serializers.CharField(source='ternak.nama')
    berat = serializers.DecimalField(source='ternak.berat', max_digits=10, decimal_places=2)
    umur = serializers.IntegerField(source='ternak.umur')
    foto = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['nama', 'berat', 'umur', 'harga', 'foto']

    def get_foto(self, obj):
        request = self.context.get('request')
        if obj.ternak.foto:
            url = obj.ternak.foto.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class CustomerPesananMazdafarmSerializer(serializers.ModelSerializer):
    """
    PBI-External-1: Serializer Read Order Mazdafarm untuk Customer.
    Hanya menampilkan data milik customer yang login.
    Tidak ada data internal (data_customer, log_pembayaran).
    """
    id_pesanan = serializers.IntegerField(source='id', read_only=True)
    daftar_ternak = CustomerOrderItemMazdafarmSerializer(source='items', many=True, read_only=True)
    total_item = serializers.SerializerMethodField()
    tagihan = serializers.DecimalField(
        source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True
    )
    menunggu_persetujuan = serializers.DecimalField(
        source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True
    )
    sudah_dibayar = serializers.DecimalField(
        source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Pesanan
        fields = [
            'id_pesanan', 'daftar_ternak', 'total_item',
            'tagihan', 'menunggu_persetujuan', 'sudah_dibayar',
            'status_pesanan', 'created_at',
        ]

    def get_total_item(self, obj):
        return len(obj.items.all())


class CustomerOrderItemMazdagingSerializer(serializers.ModelSerializer):
    """
    PBI-External-2: Item daging dalam order untuk tampilan Customer.
    """
    kode_produk = serializers.CharField(source='daging.id_daging')
    nama = serializers.CharField(source='daging.nama')

    class Meta:
        model = OrderItemDaging
        fields = ['kode_produk', 'nama', 'berat_pesanan_kg', 'harga_per_kg', 'subtotal_item']


class CustomerPesananMazdagingSerializer(serializers.ModelSerializer):
    """
    PBI-External-2: Serializer Read Order Mazdaging untuk Customer.
    Memuat kode_produk, berat_pesanan, total_harga, order_status, created_at.
    """
    id_pesanan = serializers.IntegerField(source='id', read_only=True)
    daftar_item = CustomerOrderItemMazdagingSerializer(source='items', many=True, read_only=True)
    total_item = serializers.SerializerMethodField()
    total_harga = serializers.DecimalField(
        source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True
    )
    sudah_dibayar = serializers.DecimalField(
        source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True
    )
    menunggu_persetujuan = serializers.DecimalField(
        source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True
    )
    order_status = serializers.CharField(source='status_pesanan')

    class Meta:
        model = PesananDaging
        fields = [
            'id_pesanan', 'daftar_item', 'total_item',
            'total_harga', 'sudah_dibayar', 'menunggu_persetujuan',
            'order_status', 'created_at',
        ]

    def get_total_item(self, obj):
        return len(obj.items.all())

# ── PBI-39: Laporan Penjualan Serializer ──────────────────────────────────────
class LaporanPenjualanItemSerializer(serializers.Serializer):
    """PBI-39: Single completed order row for sales report."""
    id_pesanan       = serializers.IntegerField()
    nama_customer    = serializers.CharField()
    jenis_layanan    = serializers.CharField()
    total_tagihan    = serializers.DecimalField(max_digits=15, decimal_places=2)
    tanggal_transaksi = serializers.DateTimeField()

# ── PBI-34: External Invest Order Serializer (Customer read-only) ─────────────

class OrderItemInvestExternalSerializer(serializers.ModelSerializer):
    """PBI-34: Item detail invest untuk customer (read-only)."""
    id_invest         = serializers.CharField(source='invest.id_invest')
    nama              = serializers.CharField(source='invest.nama_paket')
    berat             = serializers.DecimalField(source='invest.berat', max_digits=10, decimal_places=2, allow_null=True)
    umur              = serializers.SerializerMethodField()
    harga_sapi        = serializers.DecimalField(max_digits=15, decimal_places=2)
    harga_jual_per_kg = serializers.DecimalField(source='invest.harga_jual', max_digits=15, decimal_places=2)
    foto              = serializers.ImageField(source='invest.foto', allow_null=True)
    status_investernak = serializers.CharField(source='invest.status_investernak')

    class Meta:
        model = OrderItemInvest
        fields = ['id_invest', 'nama', 'berat', 'umur', 'harga_sapi', 'harga_jual_per_kg', 'foto', 'status_investernak']

    def get_umur(self, obj):
        """Durasi investasi dalam hari dari katalog."""
        return obj.invest.durasi_hari


class PesananInvestExternalSerializer(serializers.ModelSerializer):
    """PBI-34: Serializer pesanan invest untuk customer (read-only)."""
    id_pesanan   = serializers.IntegerField(source='id', read_only=True)
    daftar_invest = OrderItemInvestExternalSerializer(source='items', many=True, read_only=True)
    total_item            = serializers.SerializerMethodField()
    tagihan               = serializers.DecimalField(source='pembayaran.tagihan', max_digits=15, decimal_places=2, read_only=True)
    sudah_dibayar         = serializers.DecimalField(source='pembayaran.sudah_dibayar', max_digits=15, decimal_places=2, read_only=True)
    menunggu_persetujuan  = serializers.DecimalField(source='pembayaran.menunggu_persetujuan', max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = PesananInvest
        fields = [
            'id_pesanan', 'status_pesanan', 'created_at',
            'daftar_invest', 'total_item', 'tagihan', 'sudah_dibayar', 'menunggu_persetujuan',
        ]

    def get_total_item(self, obj):
        return len(obj.items.all())

class HistoriBeratSerializer(serializers.ModelSerializer):
    """PBI-37/38: Histori berat mingguan."""
    class Meta:
        model = HistoriBerat
        fields = ['id', 'tanggal_input', 'berat_kg', 'keterangan', 'estimasi_harga_jual', 'created_at']
        read_only_fields = ['estimasi_harga_jual', 'created_at']


class HistoriBeratInputSerializer(serializers.Serializer):
    """PBI-37: Input berat mingguan (Marketing/SuperAdmin)."""
    tanggal_input = serializers.DateField()
    berat_kg      = serializers.DecimalField(max_digits=10, decimal_places=2)
    keterangan    = serializers.CharField(required=False, allow_blank=True)

    def validate_berat_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Berat harus lebih dari 0.")
        return value


class PerhitunganAkhirSerializer(serializers.Serializer):
    """PBI-37: Perhitungan akhir investasi (hanya saat status = Selesai)."""
    harga_jual_aktual  = serializers.DecimalField(max_digits=15, decimal_places=2)
    biaya_pakan        = serializers.DecimalField(max_digits=15, decimal_places=2)
    biaya_operasional  = serializers.DecimalField(max_digits=15, decimal_places=2)
    biaya_obat_vitamin = serializers.DecimalField(max_digits=15, decimal_places=2)
    fee_marketing      = serializers.DecimalField(max_digits=15, decimal_places=2)

    def validate(self, data):
        for field in ['harga_jual_aktual', 'biaya_pakan', 'biaya_operasional', 'biaya_obat_vitamin', 'fee_marketing']:
            if data.get(field, 0) < 0:
                raise serializers.ValidationError(f"{field} tidak boleh negatif.")
        return data

class LaporanInvestasiSerializer(serializers.ModelSerializer):
    """Laporan investasi"""
    id_pesanan     = serializers.IntegerField(source='pesanan.id', read_only=True)
    status_pesanan = serializers.CharField(source='pesanan.status_pesanan', read_only=True)
    histori_berat  = HistoriBeratSerializer(many=True, read_only=True)
    harga_beli     = serializers.SerializerMethodField()
    info_invest    = serializers.SerializerMethodField()

    class Meta:
        model = LaporanInvestasi
        fields = [
            'id', 'id_pesanan', 'status_pesanan',
            'harga_jual_per_kg', 'target_berat_kg', 'harga_beli', 'info_invest',
            'histori_berat',
            # Final calculation fields
            'harga_jual_aktual', 'biaya_pakan', 'biaya_operasional',
            'biaya_obat_vitamin', 'fee_marketing',
            'laba_kotor', 'total_biaya', 'laba_bersih', 'bagi_hasil_investor',
            'created_at', 'updated_at',
        ]

    def get_harga_beli(self, obj):
        try:
            return float(obj.pesanan.pembayaran.sudah_dibayar)
        except Exception:
            return None

    def get_info_invest(self, obj):
        """Returns invest item info for the first invest item in the pesanan."""
        items = obj.pesanan.items.select_related('invest').all()
        result = []
        for item in items:
            inv = item.invest
            result.append({
                'nama': inv.nama_paket,
                'berat_awal': float(inv.berat) if inv.berat else None,
                'durasi_hari': inv.durasi_hari,
                'foto': inv.foto.url if inv.foto else None,
                'harga_beli': float(item.harga_sapi),
            })
        return result

