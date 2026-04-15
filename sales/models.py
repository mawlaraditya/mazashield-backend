from django.db import models
from django.conf import settings
from catalogs.models import Ternak, Invest

# ── MAZDAFARM ORDERS (PBI-23, PBI-24, PBI-25) ─────────────────────────
class Pesanan(models.Model):
    STATUS_CHOICES = [
        ('Diproses', 'Diproses'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Diproses')
    catatan = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True) 

    class Meta:
        db_table = 'pesanan'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan {self.id} - {self.customer.nama}"

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
        ('Diproses', 'Diproses'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_daging_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Diproses')
    catatan = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_daging_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pesanan_daging'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan Daging {self.id} - {self.customer.nama}"

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
        ('Diproses', 'Diproses'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pesanan_invest_customer')
    status_pesanan = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Diproses')
    catatan = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pesanan_invest_updated_by')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pesanan_invest'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan Invest {self.id} - {self.customer.nama}"


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
