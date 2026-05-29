
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from accounts.permissions import IsMarketingOrSuperAdmin
from .models import Ternak, Daging, Invest
from .pagination import CatalogPagination

from .serializers import (
    TernakCreateSerializer, TernakUpdateSerializer, TernakSerializer, TernakPublicSerializer,
    InvestCreateSerializer, InvestUpdateSerializer, InvestSerializer,
    DagingCreateSerializer, DagingUpdateSerializer, DagingSerializer, DagingPublicSerializer
)
from .filters import TernakFilter, DagingFilter, InvestFilter

# Mixin to add Cache-Control: public, max-age=60 on list responses
class PublicCacheMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.method == 'GET':
            response['Cache-Control'] = 'public, max-age=60'
        return response

# Mazdafarm (Internal)
@method_decorator(cache_page(60 * 15), name='get')
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
        # Strip id_ternak from incoming data — always auto-generated
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data.pop('id_ternak', None)
        
        serializer = TernakCreateSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(TernakSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        errors = serializer.errors
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
@method_decorator(cache_page(60 * 15), name='get')
class DagingInternalListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsMarketingOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DagingFilter

    def get_queryset(self):
        # Optimized: Added better ordering and ensuring lean queryset for list views
        return Daging.objects.filter(deleted_at__isnull=True).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DagingCreateSerializer
        return DagingSerializer

    def create(self, request, *args, **kwargs):
        # Strip id_daging from incoming data — always auto-generated
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data.pop('id_daging', None)
        
        serializer = DagingCreateSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(DagingSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
@method_decorator(cache_page(60 * 15), name='get')
class TernakPublicListView(PublicCacheMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    serializer_class = TernakPublicSerializer
    filterset_class = TernakFilter
    pagination_class = CatalogPagination

    def get_queryset(self):
        current_year = timezone.now().year
        return Ternak.objects.filter(
            deleted_at__isnull=True,
            created_at__year=current_year
        ).only(
            'id', 'id_ternak', 'nama', 'jenis', 'kelas', 'berat',
            'tanggal_penimbangan', 'berat_target', 'tanggal_lahir',
            'harga', 'deskripsi', 'foto', 'status_ternak', 'created_at', 'updated_at'
        ).annotate(
            status_order=Case(
                When(status_ternak='Available', then=Value(1)),
                When(status_ternak='Booked', then=Value(2)),
                When(status_ternak='Sold Out', then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        ).order_by('status_order', '-created_at')


@method_decorator(cache_page(60 * 15), name='get')
class DagingPublicListView(PublicCacheMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    serializer_class = DagingPublicSerializer
    filterset_class = DagingFilter
    pagination_class = CatalogPagination

    def get_queryset(self):
        current_year = timezone.now().year
        return Daging.objects.filter(
            deleted_at__isnull=True,
            created_at__year=current_year
        ).only(
            'id', 'id_daging', 'nama', 'bagian', 'harga_per_kg',
            'deskripsi', 'foto', 'status_daging', 'created_at', 'updated_at'
        ).annotate(
            status_order=Case(
                When(status_daging='Tersedia', then=Value(1)),
                When(status_daging='Habis', then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('status_order', '-created_at')


        
# ══════════════════════════════════════════════════════════════════
#  INVEST TERNAK — Internal (PBI Invest)
# ══════════════════════════════════════════════════════════════════

@method_decorator(cache_page(60 * 15), name='get')
class InvestInternalListCreateView(generics.ListCreateAPIView):
    """
    PBI-18 POST   /api/sales/invest  → Create Katalog Invest Ternak
    GET    /api/sales/invest  → Read Internal
    """
    permission_classes = [IsMarketingOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = InvestFilter

    def get_queryset(self):
        return Invest.objects.filter(deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InvestCreateSerializer
        return InvestSerializer

    def create(self, request, *args, **kwargs):
        # Strip id_invest from incoming data — always auto-generated
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data.pop('id_invest', None)
        
        serializer = InvestCreateSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(
                InvestSerializer(obj, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestInternalDetailView(APIView):
    """
    PBI-19 PUT  /api/sales/invest/<id>  → Update
    PBI-20 DELETE  /api/sales/invest/<id>  → Soft Delete
    """
    permission_classes = [IsMarketingOrSuperAdmin]

    def get_object(self, pk):
        try:
            return Invest.objects.get(pk=pk, deleted_at__isnull=True)
        except Invest.DoesNotExist:
            return None

    def put(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Invest tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvestUpdateSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(InvestSerializer(updated, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Invest tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        obj.soft_delete()
        return Response({'message': 'Invest berhasil dihapus'}, status=status.HTTP_200_OK)


@method_decorator(cache_page(60 * 15), name='get')
class InvestPublicListView(PublicCacheMixin, generics.ListAPIView):
    """
    GET /api/invest  → Public catalog Invest Ternak
    Dapat diakses oleh semua user (AllowAny) - termasuk yang belum login
    Hanya menampilkan invest yang tidak di-soft delete
    """
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    serializer_class = InvestSerializer
    filterset_class = InvestFilter
    pagination_class = CatalogPagination

    def get_queryset(self):
        current_year = timezone.now().year
        return Invest.objects.filter(
            deleted_at__isnull=True,
            created_at__year=current_year
        ).only(
            'id', 'id_invest', 'nama_paket', 'harga_sapi', 'biaya_pemeliharaan',
            'vaksin_vitamin', 'fee_marketing', 'total_modal', 'harga_jual',
            'keuntungan', 'hasil_investor', 'roi_persen',
            'jenis', 'berat', 'durasi_hari', 'deskripsi', 'foto', 'status_investernak',
            'created_at', 'updated_at'
        ).order_by('-created_at')


