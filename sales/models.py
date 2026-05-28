from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from catalogs.models import Ternak, Invest

# ── MAZDAFARM ORDERS (PBI-23, PBI-24, PBI-25) ─────────────────────────
class Pesanan(models.Model):
    STATUS_CHOICES = [
        ('Processed', 'Processed'),
                ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processed')
    catatan = models.TextField(null=True, blank=True)
    ongkir = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True) 
    
    payment_logs = GenericRelation('RiwayatPembayaran', related_query_name='pesanan_logs')

    class Meta:
        db_table = 'pesanan'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan {self.formatted_id_pesanan} - {self.customer.nama}"

    @property
    def formatted_id_pesanan(self):
        urutan = f"{self.id + 100:04d}" if self.id else "0000"
        bulan = f"{self.created_at.month:02d}" if self.created_at else "00"
        tahun = f"{self.created_at.year}" if self.created_at else "0000"
        return f"{urutan}/MZF/{bulan}/{tahun}"

class OrderItem(models.Model):
    pesanan = models.ForeignKey(Pesanan, on_delete=models.CASCADE, related_name='items')
    ternak = models.ForeignKey(Ternak, on_delete=models.PROTECT)
    berat_pesanan_kg = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    harga = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = 'order_item'

class Pembayaran(models.Model):
    pesanan = models.OneToOneField(Pesanan, on_delete=models.CASCADE, related_name='pembayaran')
    tagihan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    menunggu_persetujuan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sudah_dibayar = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'pembayaran'

# ── MAZDAGING ORDERS (PBI-27, PBI-28, PBI-29) ──────────────────────────
class PesananDaging(models.Model):
    STATUS_CHOICES = [
        ('Processed', 'Processed'),
                ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_daging_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processed')
    catatan = models.TextField(null=True, blank=True)
    ongkir = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_daging_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    payment_logs = GenericRelation('RiwayatPembayaran', related_query_name='pesanan_daging_logs')

    class Meta:
        db_table = 'pesanan_daging'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan Daging {self.formatted_id_pesanan} - {self.customer.nama}"

    @property
    def formatted_id_pesanan(self):
        urutan = f"{self.id + 100:04d}" if self.id else "0000"
        bulan = f"{self.created_at.month:02d}" if self.created_at else "00"
        tahun = f"{self.created_at.year}" if self.created_at else "0000"
        return f"{urutan}/SGR/{bulan}/{tahun}"

class OrderItemDaging(models.Model):
    pesanan = models.ForeignKey(PesananDaging, on_delete=models.CASCADE, related_name='items')
    daging = models.ForeignKey('catalogs.Daging', on_delete=models.PROTECT)
    berat_pesanan_kg = models.DecimalField(max_digits=10, decimal_places=2)
    harga_per_kg = models.DecimalField(max_digits=15, decimal_places=2) # Snapshot
    subtotal_item = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = 'order_item_daging'

class PembayaranDaging(models.Model):
    pesanan = models.OneToOneField(PesananDaging, on_delete=models.CASCADE, related_name='pembayaran')
    tagihan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    menunggu_persetujuan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sudah_dibayar = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'pembayaran_daging'


# ── INVEST TERNAK ORDERS ────────────────────────────────────────────────────
class PesananInvest(models.Model):
    STATUS_CHOICES = [
        ('Processed', 'Processed'),
                ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_invest_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Processed')
    catatan = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_invest_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    payment_logs = GenericRelation('RiwayatPembayaran', related_query_name='pesanan_invest_logs')

    class Meta:
        db_table = 'pesanan_invest'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan Invest {self.formatted_id_pesanan} - {self.customer.nama}"

    @property
    def formatted_id_pesanan(self):
        urutan = f"{self.id + 100:04d}" if self.id else "0000"
        bulan = f"{self.created_at.month:02d}" if self.created_at else "00"
        tahun = f"{self.created_at.year}" if self.created_at else "0000"
        return f"{urutan}/INV/{bulan}/{tahun}"


class OrderItemInvest(models.Model):
    pesanan = models.ForeignKey(PesananInvest, on_delete=models.CASCADE, related_name='items')
    invest = models.ForeignKey(Invest, on_delete=models.PROTECT)
    harga_sapi = models.DecimalField(max_digits=15, decimal_places=2)  # snapshot

    class Meta:
        db_table = 'order_item_invest'


class PembayaranInvest(models.Model):
    pesanan = models.OneToOneField(PesananInvest, on_delete=models.CASCADE, related_name='pembayaran')
    tagihan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    menunggu_persetujuan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sudah_dibayar = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'pembayaran_invest'

class RiwayatPembayaran(models.Model):
    STATUS_CHOICES = [
        ('Waiting', 'Waiting'),
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    nominal_pembayaran = models.DecimalField(max_digits=15, decimal_places=2)
    bank_pengirim = models.CharField(max_length=100)
    nomor_rekening_pengirim = models.CharField(max_length=50)
    nama_pengirim = models.CharField(max_length=255, null=True, blank=True)
    tanggal_transfer = models.DateField()
    waktu_transfer = models.TimeField()
    catatan = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Menunggu Verifikasi')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pembayaran_created')

    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pembayaran_verified')
    catatan_verifikasi = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'riwayat_pembayaran'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pembayaran {self.id} - {self.nominal_pembayaran} ({self.status})"


# ── PBI-37/38: LAPORAN HASIL INVESTASI ────────────────────────────────────────

class LaporanInvestasi(models.Model):
    """
    PBI-37: Laporan hasil investasi per pesanan invest.
    Satu pesanan invest memiliki satu laporan.
    Berisi histori berat mingguan dan (opsional) perhitungan akhir jika Selesai.
    """
    pesanan = models.OneToOneField(
        PesananInvest,
        on_delete=models.CASCADE,
        related_name='laporan',
        db_index=True,
    )

    # Harga jual per kg yang digunakan untuk estimasi (diinput oleh Marketing)
    harga_jual_per_kg = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Target panen (berat yang diharapkan di akhir)
    target_berat_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    

    # ── Perhitungan akhir (diisi saat status_pesanan = Selesai) ──────────────
    harga_jual_aktual    = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    biaya_pakan          = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    biaya_operasional    = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    biaya_obat_vitamin   = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fee_marketing        = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # ── Computed fields (auto-calculated on save) ─────────────────────────────
    laba_kotor           = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_biaya          = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    laba_bersih          = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    bagi_hasil_investor  = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_final   = models.BooleanField(default=False)

    class Meta:
        db_table = 'laporan_investasi'

    def hitung_akhir(self):
        """Auto-compute laba_kotor, total_biaya, laba_bersih, bagi_hasil_investor."""
        from decimal import Decimal
        if not self.harga_jual_aktual:
            return
        # harga_beli = sudah_dibayar on the pesanan's pembayaran
        harga_beli = self.pesanan.pembayaran.sudah_dibayar
        self.laba_kotor = Decimal(str(self.harga_jual_aktual)) - Decimal(str(harga_beli))
        self.total_biaya = (
            Decimal(str(self.biaya_pakan or 0))
            + Decimal(str(self.biaya_operasional or 0))
            + Decimal(str(self.biaya_obat_vitamin or 0))
            + Decimal(str(self.fee_marketing or 0))
        )
        self.laba_bersih = self.laba_kotor - self.total_biaya
        # Investor gets 50% of laba_bersih if positive
        if self.laba_bersih > 0:
            self.bagi_hasil_investor = self.laba_bersih * Decimal('0.5')
        else:
            self.bagi_hasil_investor = Decimal('0')

    def __str__(self):
        return f"Laporan Pesanan #{self.pesanan_id}"


class HistoriBerat(models.Model):
    """
    PBI-37: Histori berat mingguan ternak investasi.
    Setiap input berat tersimpan sebagai entri baru (tidak menimpa).
    """
    laporan = models.ForeignKey(
        LaporanInvestasi,
        on_delete=models.CASCADE,
        related_name='histori_berat',
    )
    tanggal_input        = models.DateField()
    berat_kg             = models.DecimalField(max_digits=10, decimal_places=2)
    keterangan           = models.TextField(null=True, blank=True)
    harga_per_kg         = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estimasi_harga_jual  = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'histori_berat'
        ordering = ['tanggal_input']

    def save(self, *args, **kwargs):
        from decimal import Decimal
        if not self.harga_per_kg:
            self.harga_per_kg = self.laporan.harga_jual_per_kg
        self.estimasi_harga_jual = (
            Decimal(str(self.berat_kg)) * Decimal(str(self.harga_per_kg))
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Berat {self.berat_kg}kg on {self.tanggal_input}"

