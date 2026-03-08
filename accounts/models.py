from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, nama, nomor_telepon, password=None, role='Customer'):
        if not email:
            raise ValueError('Email wajib diisi')
        user = self.model(
            email=self.normalize_email(email),
            nama=nama,
            nomor_telepon=nomor_telepon,
            role=role,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nama, nomor_telepon, password=None):
        user = self.create_user(
            email=email,
            nama=nama,
            nomor_telepon=nomor_telepon,
            password=password,
            role='SuperAdmin',
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('SuperAdmin', 'SuperAdmin'),
        ('Marketing', 'Marketing'),
        ('Finance', 'Finance'),
        ('CEO', 'CEO'),
        ('Komisaris', 'Komisaris'),
        ('Customer', 'Customer'),
        ('Investor', 'Investor'),
    ]

    nama = models.CharField(max_length=255)
    nomor_telepon = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Customer')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nama', 'nomor_telepon']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.nama} ({self.email}) — {self.role}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['deleted_at', 'is_active'])
