from rest_framework import serializers
from django.utils import timezone
from .models import Ternak, Daging, Invest

# Mazdafarm (Ternak)
class TernakCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ternak
        fields = [
            'id_ternak', 'nama', 'jenis', 'kelas', 'berat', 'tanggal_penimbangan', 
            'berat_target', 'tanggal_lahir', 'harga', 'deskripsi', 'foto', 'status_ternak'
        ]
        read_only_fields = ['id_ternak']

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
    class Meta:
        model = Ternak
        fields = [
            'nama', 'jenis', 'kelas', 'berat', 'tanggal_penimbangan', 'berat_target', 
            'tanggal_lahir', 'harga', 'deskripsi', 'foto', 'status_ternak'
        ]

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
    umur = serializers.ReadOnlyField()

    class Meta:
        model = Ternak
        fields = [
            'id', 'id_ternak', 'nama', 'jenis', 'kelas', 'berat', 'tanggal_penimbangan', 
            'berat_target', 'tanggal_lahir', 'umur', 'harga', 'deskripsi', 
            'foto', 'status_ternak', 'created_at', 'updated_at'
        ]

# Mazdaging (Daging)
class DagingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Daging
        fields = ['id_daging', 'nama', 'bagian', 'harga_per_kg', 'deskripsi', 'foto', 'status_daging']
        read_only_fields = ['id_daging']

    def validate_harga_per_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga per kg harus lebih dari 0')
        return value

class DagingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Daging
        fields = ['nama', 'bagian', 'harga_per_kg', 'deskripsi', 'foto', 'status_daging']

    def validate_harga_per_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga per kg harus lebih dari 0')
        return value
    
class DagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Daging
        fields = [
            'id', 'id_daging', 'nama', 'bagian', 'harga_per_kg', 'deskripsi', 
            'foto', 'status_daging', 'created_at', 'updated_at'
        ]


# Invest Ternak
class InvestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invest
        fields = [
            'id_invest', 'nama_paket', 'harga_sapi', 'biaya_pemeliharaan', 
            'vaksin_vitamin', 'fee_marketing', 'total_modal', 'harga_jual', 
            'keuntungan', 'hasil_investor', 'roi_persen',
            'jenis', 'berat', 'durasi_hari', 'deskripsi', 'foto', 'status_investernak'
        ]
        read_only_fields = ['id_invest']

    def validate_harga_sapi(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga sapi harus lebih dari 0')
        return value

class InvestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invest
        fields = [
            'nama_paket', 'harga_sapi', 'biaya_pemeliharaan', 
            'vaksin_vitamin', 'fee_marketing', 'total_modal', 'harga_jual', 
            'keuntungan', 'hasil_investor', 'roi_persen',
            'jenis', 'berat', 'durasi_hari', 'deskripsi', 'foto', 'status_investernak'
        ]

    def validate_harga_sapi(self, value):
        if value <= 0:
            raise serializers.ValidationError('Harga sapi harus lebih dari 0')
        return value

class InvestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invest
        fields = [
            'id', 'id_invest', 'nama_paket', 'harga_sapi', 'biaya_pemeliharaan', 
            'vaksin_vitamin', 'fee_marketing', 'total_modal', 'harga_jual', 
            'keuntungan', 'hasil_investor', 'roi_persen',
            'jenis', 'berat', 'durasi_hari', 'deskripsi', 'foto', 'status_investernak',
            'created_at', 'updated_at'
        ]