from django.db import models
from django.utils import timezone

class Ternak(models.Model):
    STATUS_CHOICES = [
        ('Tersedia', 'Tersedia'),
        ('Dipesan', 'Dipesan'),
        ('Terjual', 'Terjual'),
    ]
    
    JENIS_CHOICES = [
        ('Sapi', 'Sapi'),
        ('Kambing', 'Kambing'),
    ]

    KELAS_CHOICES = [
        ('A', 'Kelas A'),
        ('B', 'Kelas B'),
        ('C', 'Kelas C'),
        ('D', 'Kelas D'),
        ('E', 'Kelas E'),
        ('Patungan', 'Patungan'),
    ]

    id_ternak = models.CharField(max_length=50, unique=True)
    nama = models.CharField(max_length=255)
    jenis = models.CharField(max_length=100, choices=JENIS_CHOICES, default='Sapi')
    kelas = models.CharField(max_length=20, choices=KELAS_CHOICES, null=True, blank=True)
    berat = models.DecimalField(max_digits=10, decimal_places=2)
    tanggal_penimbangan = models.DateField(default=timezone.now)
    berat_target = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tanggal_lahir = models.DateField(null=True, blank=True)
    harga = models.DecimalField(max_digits=15, decimal_places=2)
    deskripsi = models.TextField()
    foto = models.ImageField(upload_to='ternak/', null=True, blank=True)
    status_ternak = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Tersedia')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ternak'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id_ternak} — {self.nama}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    @property
    def umur(self):
        if not self.tanggal_lahir:
            return 0
        today = timezone.now().date()
        return (today.year - self.tanggal_lahir.year) * 12 + today.month - self.tanggal_lahir.month

class Daging(models.Model):
    STATUS_CHOICES = [
        ('Tersedia', 'Tersedia'),
        ('Terjual', 'Terjual'),
        ('Pre Order', 'Pre Order'),
    ]

    id_daging = models.CharField(max_length=50, unique=True)
    nama = models.CharField(max_length=255)
    bagian = models.CharField(max_length=100)
    harga_per_kg = models.DecimalField(max_digits=15, decimal_places=2)
    deskripsi = models.TextField()
    foto = models.ImageField(upload_to='daging/', null=True, blank=True)
    status_daging = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Tersedia')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'daging'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id_daging} — {self.nama}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])


class Invest(models.Model):
    """Katalog Invest Ternak — PBI 18-20"""
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Ongoing', 'Ongoing'),
        ('Closed', 'Closed'),
    ]

    id_invest = models.CharField(max_length=50, unique=True)
    nama_paket = models.CharField(max_length=255)
    harga_sapi = models.DecimalField(max_digits=15, decimal_places=2)
    biaya_pemeliharaan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    vaksin_vitamin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fee_marketing = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_modal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    harga_jual = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    keuntungan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    hasil_investor = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    roi_persen = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    jenis = models.CharField(max_length=100, default='Sapi')
    berat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    durasi_hari = models.IntegerField(default=120)
    deskripsi = models.TextField(null=True, blank=True)
    foto = models.ImageField(upload_to='invest/', null=True, blank=True)
    status_investernak = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'invest'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id_invest} — {self.nama_paket}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

