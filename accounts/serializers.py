from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import User


# ─── PBI-1: Register Customer ─────────────────────────────────────────────────
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'email', 'password']

    def validate_email(self, value):
        if User.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('Email sudah terdaftar')
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            nama=validated_data['nama'],
            nomor_telepon=validated_data['nomor_telepon'],
            password=validated_data['password'],
            role='Customer',
        )


# ─── PBI-2: Login ─────────────────────────────────────────────────────────────
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Email atau password salah', code='unauthorized')
        if not user.is_active or user.deleted_at is not None:
            raise serializers.ValidationError('Akun tidak aktif', code='forbidden')
        # Update last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        data['user'] = user
        return data
    

# ─── PBI-5: Edit Profile ──────────────────────────────────────────────────────
class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'email', 'role']

    def update(self, instance, validated_data):
        instance.nama = validated_data.get('nama', instance.nama)
        instance.nomor_telepon = validated_data.get('nomor_telepon', instance.nomor_telepon)
        instance.updated_at = timezone.now()
        instance.save(update_fields=['nama', 'nomor_telepon', 'updated_at'])
        return instance
    
# ─── User List (for admin) ────────────────────────────────────────────────────
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nama', 'nomor_telepon', 'email', 'role', 'is_active', 'created_at']


# ─── Admin Edit User (for admin) ──────────────────────────────────────────────
class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'role', 'is_active']

    def update(self, instance, validated_data):
        new_active_status = validated_data.get('is_active', instance.is_active)
        
        # If reactivating, clear deleted_at
        if new_active_status and not instance.is_active:
            instance.deleted_at = None
            
        instance.nama = validated_data.get('nama', instance.nama)
        instance.nomor_telepon = validated_data.get('nomor_telepon', instance.nomor_telepon)
        instance.role = validated_data.get('role', instance.role)
        instance.is_active = new_active_status
        instance.updated_at = timezone.now()
        instance.save()
        return instance