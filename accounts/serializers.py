from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import User

# Register Customer
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'email', 'password']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value, deleted_at__isnull=True).exists():
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

# Login
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Email atau password salah', code='unauthorized')
        if not user.is_active or user.deleted_at is not None:
            raise serializers.ValidationError('Akun tidak aktif', code='forbidden')
        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        data['user'] = user
        return data
<<<<<<< HEAD


# ─── PBI-4: Register by Admin ─────────────────────────────────────────────────
VALID_ROLES = [r[0] for r in User.ROLE_CHOICES]

class AdminRegisterSerializer(serializers.ModelSerializer):
    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'email', 'role', 'generated_password']

    def validate_role(self, value):
        request_user = self.context.get('request').user
        if value not in VALID_ROLES:
            raise serializers.ValidationError(f'Role tidak valid. Pilihan: {VALID_ROLES}')
        
        # 1. Marketing can ONLY create Customer
        if request_user.role == 'Marketing' and value != 'Customer':
            raise serializers.ValidationError('Marketing hanya dapat membuat akun Customer')
        
        # 2. CEO dan Komisaris itu 1 orang (mencegah duplikasi peran jika sudah ada)
        if value in ['CEO', 'Komisaris']:
            if User.objects.filter(role__in=['CEO', 'Komisaris']).exists():
                raise serializers.ValidationError('Role CEO/Komisaris sudah ada (hanya boleh ada 1 person)')
        
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('Email sudah terdaftar')
        return value

    def create(self, validated_data):
        # Generate random password
        random_pwd = get_random_string(length=12)
        validated_data['password'] = random_pwd
        user = User.objects.create_user(**validated_data)
        # Store for display in response
        user.generated_password = random_pwd
        return user


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


# ─── PBI-6: Change Password ───────────────────────────────────────────────────
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({'old_password': 'Password lama salah'})
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({'new_password': 'Password baru tidak boleh sama dengan password lama'})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.updated_at = timezone.now()
        user.save(update_fields=['password', 'updated_at'])
        return user


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
=======
>>>>>>> 9c30bed2f80a9b46649c9ca0451f6c189e130ad6

# Register by Admin
VALID_ROLES = [r[0] for r in User.ROLE_CHOICES]

class AdminRegisterSerializer(serializers.ModelSerializer):
    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'email', 'role', 'generated_password']

    def validate_role(self, value):
        request_user = self.context.get('request').user
        if value not in VALID_ROLES:
            raise serializers.ValidationError(f'Role tidak valid. Pilihan: {VALID_ROLES}')
        
        if request_user.role == 'Marketing' and value not in ['Customer', 'Investor']:
            raise serializers.ValidationError('Marketing hanya diperbolehkan membuat akun Customer atau Investor')
        
        if value in ['CEO', 'Komisaris']:
            if User.objects.filter(role__in=['CEO', 'Komisaris']).exists():
                raise serializers.ValidationError('Role CEO/Komisaris sudah ada')
        
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email sudah terdaftar')
        return value

    def create(self, validated_data):
        random_pwd = get_random_string(length=12)
        validated_data['password'] = random_pwd
        user = User.objects.create_user(**validated_data)
        user.generated_password = random_pwd
        return user

# Profile
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

# Change Password
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({'old_password': 'Password lama salah'})
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({'new_password': 'Password baru tidak boleh sama dengan password lama'})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.updated_at = timezone.now()
        user.save(update_fields=['password', 'updated_at'])
        return user

# Admin User Management
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nama', 'nomor_telepon', 'email', 'role', 'is_active', 'created_at']

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['nama', 'nomor_telepon', 'role']

    def update(self, instance, validated_data):
        if instance.deleted_at is not None or not instance.is_active:
             raise serializers.ValidationError({'detail': 'Akun ini sudah dinonaktifkan.'})

        instance.nama = validated_data.get('nama', instance.nama)
        instance.nomor_telepon = validated_data.get('nomor_telepon', instance.nomor_telepon)
        instance.role = validated_data.get('role', instance.role)
        instance.updated_at = timezone.now()
        instance.save()
        return instance

# Forgot & Reset Password
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('Email tidak ditemukan')
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        from .models import ResetPasswordOTP
        email = data.get('email')
        token = data.get('token')
        
        otp_record = ResetPasswordOTP.objects.filter(
            user__email__iexact=email, 
            otp=token, 
            is_used=False
        ).last()

        if not otp_record:
            exists = ResetPasswordOTP.objects.filter(user__email__iexact=email, otp=token).exists()
            if exists:
                raise serializers.ValidationError('Link ini sudah pernah digunakan.')
            raise serializers.ValidationError('Link reset password tidak valid.')
        
        if not otp_record.is_valid():
            raise serializers.ValidationError('Link reset password sudah kadaluarsa.')
        
        data['user'] = otp_record.user
        data['otp_record'] = otp_record
        return data

    def save(self):
        user = self.validated_data['user']
        otp_record = self.validated_data['otp_record']
        
        user.set_password(self.validated_data['new_password'])
        user.save()
        
        otp_record.is_used = True
        otp_record.save()
        
        return user
