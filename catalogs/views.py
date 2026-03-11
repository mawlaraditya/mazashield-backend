from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsMarketingOrSuperAdmin
from .models import Ternak, Daging
from .serializers import (
    TernakCreateSerializer, TernakUpdateSerializer, TernakSerializer,
    DagingCreateSerializer, DagingUpdateSerializer, DagingSerializer
)
from .filters import TernakFilter, DagingFilter

# Mazdafarm (Internal)
class TernakInternalListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsMarketingOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TernakFilter

    def get_queryset(self):
        return Ternak.objects.filter(deleted_at__isnull=True).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TernakCreateSerializer
        return TernakSerializer

    def create(self, request, *args, **kwargs):
        serializer = TernakCreateSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(TernakSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        errors = serializer.errors
        if 'id_ternak' in errors and any('sudah' in str(e) for e in errors['id_ternak']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

class TernakInternalDetailView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def get_object(self, pk):
        try:
            return Ternak.objects.get(pk=pk, deleted_at__isnull=True)
        except Ternak.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Ternak tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TernakUpdateSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(TernakSerializer(updated, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Ternak tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        obj.soft_delete()
        return Response({'message': 'Ternak berhasil dihapus'}, status=status.HTTP_200_OK)

# Mazdaging (Internal)
class DagingInternalListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsMarketingOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DagingFilter

    def get_queryset(self):
        return Daging.objects.filter(deleted_at__isnull=True).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DagingCreateSerializer
        return DagingSerializer

    def create(self, request, *args, **kwargs):
        serializer = DagingCreateSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(DagingSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        errors = serializer.errors
        if 'id_daging' in errors and any('sudah' in str(e) for e in errors['id_daging']):
            return Response(errors, status=status.HTTP_409_CONFLICT)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

class DagingInternalDetailView(APIView):
    permission_classes = [IsMarketingOrSuperAdmin]

    def get_object(self, pk):
        try:
            return Daging.objects.get(pk=pk, deleted_at__isnull=True)
        except Daging.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Daging tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DagingUpdateSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(DagingSerializer(updated, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Daging tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        obj.soft_delete()
        return Response({'message': 'Daging berhasil dihapus'}, status=status.HTTP_200_OK)

# Public Views
class TernakPublicListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    serializer_class = TernakSerializer
    filterset_class = TernakFilter

    def get_queryset(self):
        return Ternak.objects.filter(deleted_at__isnull=True).order_by('-created_at')

class DagingPublicListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    serializer_class = DagingSerializer
    filterset_class = DagingFilter

    def get_queryset(self):
        return Daging.objects.filter(deleted_at__isnull=True).order_by('-created_at')