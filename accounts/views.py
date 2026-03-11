from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import csv
import os
from django.http import HttpResponse
from django.utils import timezone

from django.core.mail import send_mail
from django.conf import settings

from .models import User, ResetPasswordOTP
from .serializers import (
    RegisterSerializer, LoginSerializer, AdminRegisterSerializer,
    ProfileSerializer, ChangePasswordSerializer, UserListSerializer,
    AdminUserUpdateSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
)
from .permissions import IsSuperAdmin, IsMarketingOrSuperAdmin, IsActiveUser

# ─── PBI-1: Register Customer ─────────────────────────────────────────────────
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Registrasi berhasil'},
                status=status.HTTP_201_CREATED
            )
        # Differentiate 409 vs 400
        errors = serializer.errors
        if 'email' in errors and any('sudah terdaftar' in str(e) for e in errors['email']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


# ─── PBI-2: Login ─────────────────────────────────────────────────────────────
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


# ─── PBI-4: Register by Admin ─────────────────────────────────────────────────
class AdminRegisterView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def post(self, request):
        serializer = AdminRegisterSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Akun berhasil dibuat',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        errors = serializer.errors
        if 'email' in errors and any('sudah terdaftar' in str(e) for e in errors['email']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


# ─── PBI-5: Edit Profile ──────────────────────────────────────────────────────
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


# ─── PBI-6: Change Password ───────────────────────────────────────────────────
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
        queryset = User.objects.all().order_by('-created_at')
        account_type = self.request.query_params.get('type')
        
        if account_type == 'internal':
            queryset = queryset.filter(role__in=['SuperAdmin', 'Marketing', 'Finance', 'CEO', 'Komisaris'])
        elif account_type == 'external':
            queryset = queryset.filter(role__in=['Customer', 'Investor'])
            
        # Basic Search (Non-django-filter implementation)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(nama__icontains=search) | 
                Q(email__icontains=search) | 
                Q(nomor_telepon__icontains=search)
            )

        # Status Filter
        status_param = self.request.query_params.get('status')
        if status_param == 'Aktif':
            queryset = queryset.filter(is_active=True)
        elif status_param == 'Nonaktif':
            queryset = queryset.filter(is_active=False)

        # Role Filter
        role_param = self.request.query_params.get('role')
        if role_param and role_param != 'all':
            queryset = queryset.filter(role=role_param)

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
            return Response(
                {'error': 'Anda tidak dapat menghapus akun Anda sendiri'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.soft_delete()
        return Response({'message': 'User berhasil dihapus/nonaktifkan'}, status=status.HTTP_200_OK)


# ─── Admin Update User ────────────────────────────────────────────────────────
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
        # Marketing only allowed to view (GET), but not update (PUT)
        if request.user.role != 'SuperAdmin':
            return Response({'error': 'Hanya SuperAdmin yang dapat mengedit user'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'User berhasil diperbarui', 'data': serializer.data})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)


# ─── PBI-XX: Export Users to CSV ──────────────────────────────────────────────
class AdminUserExportView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        export_type = request.query_params.get('type', 'external')
        
        if export_type == 'internal':
            roles = ['SuperAdmin', 'Marketing', 'Finance', 'CEO', 'Komisaris']
            filename = f"akun_internal_{timezone.now().strftime('%Y%m%d')}.csv"
        else:
            roles = ['Customer', 'Investor']
            filename = f"akun_external_{timezone.now().strftime('%Y%m%d')}.csv"

        users = User.objects.filter(role__in=roles).order_by('-created_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        # Header
        writer.writerow(['ID', 'Nama', 'Email', 'Nomor Telepon', 'Role', 'Status', 'Tanggal Dibuat'])
        
        # Data
        for user in users:
            status = 'Aktif' if user.is_active else 'Nonaktif'
            created_at = user.created_at.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([
                user.id, 
                user.nama, 
                user.email, 
                user.nomor_telepon, 
                user.role, 
                status, 
                created_at
            ])
            
        return response


import threading
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# ─── PBI-XP: Forgot & Reset Password (Token via Email) ────────────────────────
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # 1. Generate Secure Token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            
            # 2. Simpan ke database
            ResetPasswordOTP.objects.create(user=user, otp=reset_token)
            
            # 3. Create Direct Reset Link
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/forgot-password?token={reset_token}&email={email}"
            
            # 4. Kirim Email di Background
            def send_reset_email():
                subject = 'MazaShield - Permintaan Reset Password'
                
                context = {
                    'nama': user.nama,
                    'reset_link': reset_link,
                }
                
                html_content = render_to_string('accounts/email/reset_password_email.html', context)
                text_content = strip_tags(html_content)
                
                try:
                    send_mail(
                        subject, 
                        text_content, 
                        settings.EMAIL_HOST_USER, 
                        [email], 
                        html_message=html_content,
                        fail_silently=False
                    )
                    print(f"SUCCESS: Reset email sent to {email}")
                except Exception as e:
                    print(f"EMAIL ERROR: {e}")

            threading.Thread(target=send_reset_email).start()
            
            return Response({
                'message': 'Link reset password telah dikirim ke email Anda'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password berhasil diperbarui. Silakan login kembali.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
