from rest_framework import serializers
from django.utils import timezone
from .models import Ternak


# ══════════════════════════════════════════════════════════════════
#  MAZDAFARM — Ternak (PBI 8–12)
# ══════════════════════════════════════════════════════════════════

class TernakCreateSerializer(serializers.ModelSerializer):
    """PBI-8: Create Katalog Mazdafarm"""

    class Meta:
        model = Ternak
        fields = [
            'id_ternak', 'nama', 'jenis', 'berat', 'tanggal_penimbangan', 'berat_target', 'tanggal_lahir', 'harga',
            'deskripsi', 'foto', 'status_ternak',
        ]

    def validate_id_ternak(self, value):
        if Ternak.objects.filter(id_ternak=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('ID Ternak sudah digunakan')
        return value

    def validate_berat(self, value):
        if value <= 0:
            raise serializers.ValidationError('Berat harus lebih dari 0')
        return value
    
    def validate_berat_target(self, value):
        if value <= 0:
            raise serializers.ValidationError('Berat target harus lebih dari 0')
        return value

    def validate_harga(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga harus lebih dari 0')
        return value


class TernakUpdateSerializer(serializers.ModelSerializer):
    """PBI-9: Update Katalog Mazdafarm"""

    class Meta:
        model = Ternak
        fields = ['nama', 'jenis', 'berat', 'tanggal_penimbangan', 'berat_target', 'tanggal_lahir', 'harga', 'deskripsi', 'foto', 'status_ternak']

    def validate_berat(self, value):
        if value <= 0:
            raise serializers.ValidationError('Berat harus lebih dari 0')
        return value
    
    def validate_tanggal_penimbangan(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Tanggal penimbangan tidak boleh di masa depan")
        return value
    
    def validate_berat_target(self, value):
        if value <= 0:
            raise serializers.ValidationError('Berat target harus lebih dari 0')
        return value

    def validate_harga(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga harus lebih dari 0')
        return value

class TernakSerializer(serializers.ModelSerializer):
    """PBI-11 & PBI-12: Read Katalog Mazdafarm"""
    umur = serializers.ReadOnlyField()

    class Meta:
        model = Ternak
        fields = [
            'id', 'id_ternak', 'nama', 'jenis', 'berat', 'tanggal_penimbangan', 'berat_target', 'tanggal_lahir', 'umur', 'harga',
            'deskripsi', 'foto', 'status_ternak', 'created_at', 'updated_at',
        ]


