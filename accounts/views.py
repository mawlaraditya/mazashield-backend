import csv
import os
import threading
import urllib.parse

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, ResetPasswordOTP
from .serializers import (
    RegisterSerializer, LoginSerializer, AdminRegisterSerializer,
    ProfileSerializer, ChangePasswordSerializer, UserListSerializer,
    AdminUserUpdateSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
)
from .permissions import IsSuperAdmin, IsMarketingOrSuperAdmin, IsActiveUser

# Register Customer
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Registrasi berhasil'}, status=status.HTTP_201_CREATED)
        
        errors = serializer.errors
        if 'email' in errors and any('sudah terdaftar' in str(e) for e in errors['email']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

# Login
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            error_codes = [e.code for errors in serializer.errors.values() for e in errors]
            if 'forbidden' in error_codes:
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'nama': user.nama,
        }, status=status.HTTP_200_OK)
    
# ─── PBI-3: Logout ────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)

# Logout
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)
        except (TokenError, Exception):
            return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)

# Admin Register User
class AdminRegisterView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def post(self, request):
        serializer = AdminRegisterSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Akun berhasil dibuat', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        
        errors = serializer.errors
        if 'email' in errors and any('sudah terdaftar' in str(e) for e in errors['email']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

# Profile Management
class ProfileView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profil berhasil diperbarui', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsActiveUser]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password berhasil diubah'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── PBI-4 + PBI-7: Admin User Management ────────────────────────────────────
class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsMarketingOrSuperAdmin]
    serializer_class = UserListSerializer

    def get_queryset(self):
        # Show ALL users including soft-deleted (nonaktif), no deleted_at filter
        queryset = User.objects.all().order_by('-created_at')
        account_type = self.request.query_params.get('type')
        
        if account_type == 'internal':
            queryset = queryset.filter(role__in=['SuperAdmin', 'Marketing', 'Finance', 'CEO', 'Komisaris'])
        elif account_type == 'external':
            queryset = queryset.filter(role__in=['Customer'])
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nama__icontains=search) | 
                Q(email__icontains=search) | 
                Q(nomor_telepon__icontains=search)
            )
        return queryset


# ─── PBI-7: Soft Delete User by Admin ────────────────────────────────────────
class AdminUserDeleteView(APIView):
    permission_classes = [IsSuperAdmin]

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)

        if user.pk == request.user.pk:
            return Response({'error': 'Anda tidak dapat menghapus akun sendiri'}, status=status.HTTP_400_BAD_REQUEST)

        user.soft_delete()
        return Response({'message': 'User berhasil dinonaktifkan'}, status=status.HTTP_200_OK)

class AdminUserUpdateView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            serializer = UserListSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        if request.user.role != 'SuperAdmin':
            return Response({'error': 'Akses ditolak'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'User berhasil diperbarui', 'data': serializer.data})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)

class AdminUserExportView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def get(self, request):
        export_type = request.query_params.get('type', 'external')
        
        # Marketing can only export external accounts
        if request.user.role == 'Marketing' and export_type == 'internal':
            return Response({'error': 'Anda tidak memiliki izin mengekspor akun internal'}, status=status.HTTP_403_FORBIDDEN)

        if export_type == 'internal':
            roles = ['SuperAdmin', 'Marketing', 'Finance', 'CEO', 'Komisaris']
            filename = f"internal_{timezone.now().strftime('%Y%m%d')}.csv"
        else:
            roles = ['Customer']
            filename = f"external_{timezone.now().strftime('%Y%m%d')}.csv"

        # Include all users (active AND nonaktif/soft-deleted)
        users = User.objects.filter(role__in=roles).order_by('-created_at')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Nama', 'Email', 'Telepon', 'Role', 'Status', 'Dibuat'])
        
        for u in users:
            stat = 'Aktif' if u.is_active else 'Nonaktif'
            date = u.created_at.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')
            writer.writerow([u.id, u.nama, u.email, u.nomor_telepon, u.role, stat, date])
            
        return response

# Forgot & Reset Password
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        email = serializer.validated_data['email']
        
        # Always return 200 immediately to prevent email enumeration and provide fast response
        response = Response({'message': 'Link reset password akan dikirim jika email terdaftar.'}, status=status.HTTP_200_OK)
        
        # User lookup is fast enough to do here before threading
        user = User.objects.filter(email__iexact=email, deleted_at__isnull=True).first()
        
        if user:
            import secrets
            # 1. Prepare data (Fast DB ops)
            reset_token = secrets.token_urlsafe(32)
            ResetPasswordOTP.objects.create(user=user, otp=reset_token)
            
            # 2. Prepare link and content
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            safe_email = urllib.parse.quote(user.email)
            reset_link = f"{frontend_url}/forgot-password?token={reset_token}&email={safe_email}"
            
            context = {'nama': user.nama, 'reset_link': reset_link}
            html_content = render_to_string('accounts/email/reset_password_email.html', context)
            text_content = strip_tags(html_content)
            subject = 'MazaShield - Reset Password'
            recipient = user.email

            # 3. Fire and forget ONLY the network IO part
            def send_mail_async(subject, text, html, to):
                try:
                    msg = EmailMultiAlternatives(
                        subject, text, 
                        settings.EMAIL_HOST_USER, [to]
                    )
                    msg.attach_alternative(html, "text/html")
                    msg.send(fail_silently=False)
                except Exception as e:
                    print(f"SMTP Error: {e}")

            email_thread = threading.Thread(target=send_mail_async, args=(subject, text_content, html_content, recipient))
            email_thread.daemon = True
            email_thread.start()
            
        return response

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password berhasil diperbarui'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
