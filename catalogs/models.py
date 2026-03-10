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
    jenis = models.CharField(max_length=100)
    berat = models.DecimalField(max_digits=10, decimal_places=2)
    tanggal_penimbangan = models.DateField()
    berat_target = models.DecimalField(max_digits=10, decimal_places=2)
    umur = models.IntegerField() # TODO: ini kalo input susah gasi? bisa nulis lahirnya kapan aja gak nanti pake logic
    harga = models.DecimalField(max_digits=15, decimal_places=2)
    deskripsi = models.TextField()
    foto = models.ImageField(upload_to='ternak/', null=True, blank=True)
    status_ternak = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Tersedia')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # TODO: kalo pake auto_now sepertinya bisa langsung
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ternak'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id_ternak} — {self.nama}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
