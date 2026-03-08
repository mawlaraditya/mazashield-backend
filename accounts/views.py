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
