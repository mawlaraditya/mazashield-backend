from django.db import models
from django.utils import timezone


class Ternak(models.Model):
    """Katalog Mazdafarm — PBI 8-12"""
    STATUS_CHOICES = [
        ('Tersedia', 'Tersedia'),
        ('Dipesan', 'Dipesan'),
        ('Terjual', 'Terjual'),
    ]

    id_ternak = models.CharField(max_length=50, unique=True)
    nama = models.CharField(max_length=255)
    jenis = models.CharField(max_length=100, default='Sapi')
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
        """Menghitung umur dalam bulan secara real-time"""
        if not self.tanggal_lahir:
            return 0
        today = timezone.now().date()
        return (today.year - self.tanggal_lahir.year) * 12 + today.month - self.tanggal_lahir.month
