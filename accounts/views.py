from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import csv
from django.http import HttpResponse
from django.utils import timezone

from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer, AdminRegisterSerializer,
    ProfileSerializer, ChangePasswordSerializer, UserListSerializer,
    AdminUserUpdateSerializer,
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
    
# ─── PBI-4 + PBI-7: Admin User Management ────────────────────────────────────
class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsMarketingOrSuperAdmin]
    serializer_class = UserListSerializer

    def get_queryset(self):
        return User.objects.all().order_by('-created_at')


# ─── PBI-7: Soft Delete User by Admin ────────────────────────────────────────
class AdminUserDeleteView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

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
    
# ─── Export Users to CSV ──────────────────────────────────────────────
class AdminUserExportView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

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