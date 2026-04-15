from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Pesanan, OrderItem, Pembayaran, PesananDaging, OrderItemDaging, PembayaranDaging, PesananInvest, OrderItemInvest, PembayaranInvest
from .serializers import (
    PesananSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    PesananDagingSerializer, OrderDagingCreateSerializer,
    PesananInvestSerializer, OrderInvestCreateSerializer, OrderInvestUpdateSerializer,
)
from accounts.models import User
from catalogs.models import Ternak, Daging, Invest
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Q

class IsSuperAdminOrMarketing(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SuperAdmin', 'Marketing']

class OrderMazdafarmViewSet(viewsets.ModelViewSet):
    """
    Manajemen Pesanan Mazdafarm
    """
    queryset = Pesanan.objects.filter(deleted_at__isnull=True)
    serializer_class = PesananSerializer
    permission_classes = [IsSuperAdminOrMarketing]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        PBI-25: Read Internal Mazdafarm (Filter by status & created_at range)
        """
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        return queryset

    def create(self, request, *args, **kwargs):
        """
        PBI-23: Create Order Mazdafarm
        """
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        id_customer = serializer.validated_data['id_customer']
        daftar_id_ternak = serializer.validated_data['daftar_id_ternak']
        catatan = serializer.validated_data.get('catatan', '')

        # PBI-23: Jika customer tidak ditemukan → return 404 Not Found
        try:
            customer = User.objects.get(id=id_customer)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                # Validate cattle
                ternaks = []
                total_tagihan = 0
                for tid in daftar_id_ternak:
                    try:
                        ternak = Ternak.objects.select_for_update().get(id_ternak=tid)
                        if ternak.status_ternak != 'Tersedia' or ternak.deleted_at is not None:
                            return Response({"detail": f"Ternak {tid} tidak tersedia."}, status=status.HTTP_400_BAD_REQUEST)
                        ternaks.append(ternak)
                        total_tagihan += ternak.harga
                    except Ternak.DoesNotExist:
                        return Response({"detail": f"Ternak {tid} tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

                # Create Pesanan
                pesanan = Pesanan.objects.create(
                    customer=customer,
                    catatan=catatan,
                    status_pesanan='Diproses',
                    updated_at=None
                )

                # Create OrderItems and change cattle status
                for ternak in ternaks:
                    OrderItem.objects.create(
                        pesanan=pesanan,
                        ternak=ternak,
                        berat_pesanan_kg=1.00,
                        harga=ternak.harga
                    )
                    ternak.status_ternak = 'Dipesan'
                    ternak.save()

                # Create Pembayaran
                Pembayaran.objects.create(
                    pesanan=pesanan,
                    tagihan=total_tagihan,
                    menunggu_persetujuan=0,
                    sudah_dibayar=0
                )

                return Response(PesananSerializer(pesanan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        PBI-24: Update Status Pesanan Mazdafarm
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object_or_404_by_id(kwargs.get('pk'))
        
        # PBI-24: Jika pesanan sudah berstatus Selesai atau Dibatalkan → return 400
        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderUpdateSerializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data.get('status_pesanan', instance.status_pesanan)
        
        # Validation of transition
        if new_status == 'Selesai':
            pembayaran = instance.pembayaran
            if pembayaran.tagihan > 0 or pembayaran.menunggu_persetujuan > 0:
                return Response({"detail": "Masih ada sisa tagihan atau pembayaran menunggu persetujuan."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = serializer.validated_data.get('catatan', instance.catatan)
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                instance.save()

                # Sync cattle status
                items = instance.items.all()
                if new_status == 'Selesai':
                    for item in items:
                        item.ternak.status_ternak = 'Terjual'
                        item.ternak.save()
                elif new_status == 'Dibatalkan':
                    for item in items:
                        item.ternak.status_ternak = 'Tersedia'
                        item.ternak.save()

                return Response(PesananSerializer(instance).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_object_or_404_by_id(self, pk):
        try:
            return Pesanan.objects.get(pk=pk, deleted_at__isnull=True)
        except Pesanan.DoesNotExist:
            from django.http import Http404
            raise Http404("Pesanan tidak ditemukan.")

class OrderMazdagingViewSet(viewsets.ModelViewSet):
    """
    PBI-27, PBI-28, PBI-29: Manajemen Pesanan Mazdaging
    """
    queryset = PesananDaging.objects.filter(deleted_at__isnull=True)
    serializer_class = PesananDagingSerializer
    permission_classes = [IsSuperAdminOrMarketing]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        PBI-29: Read Internal Mazdaging (Filter by status & created_at range)
        """
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        return queryset

    def create(self, request, *args, **kwargs):
        """
        PBI-27: Create Order Mazdaging
        """
        serializer = OrderDagingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        id_customer = serializer.validated_data['id_customer']
        items_data = serializer.validated_data['items']
        catatan = serializer.validated_data.get('catatan', '')

        try:
            customer = User.objects.get(id=id_customer)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                # Validate meat items
                items_to_create = []
                total_tagihan = 0
                for item_data in items_data:
                    id_daging = item_data['id_daging']
                    berat_pesanan_kg = float(item_data['berat_pesanan_kg'])
                    
                    try:
                        daging = Daging.objects.select_for_update().get(id_daging=id_daging)
                        if daging.status_daging not in ['Tersedia', 'Pre Order'] or daging.deleted_at is not None:
                            return Response({"detail": f"Daging {id_daging} tidak tersedia atau Pre Order."}, status=status.HTTP_400_BAD_REQUEST)
                        
                        subtotal = float(daging.harga_per_kg) * berat_pesanan_kg
                        items_to_create.append({
                            'daging': daging,
                            'berat': berat_pesanan_kg,
                            'harga_per_kg': daging.harga_per_kg,
                            'subtotal': subtotal
                        })
                        total_tagihan += subtotal
                    except Daging.DoesNotExist:
                        return Response({"detail": f"Daging {id_daging} tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

                # Create PesananDaging
                pesanan = PesananDaging.objects.create(
                    customer=customer,
                    catatan=catatan,
                    status_pesanan='Diproses',
                    updated_at=timezone.now()
                )

                # Create OrderItems
                for item in items_to_create:
                    OrderItemDaging.objects.create(
                        pesanan=pesanan,
                        daging=item['daging'],
                        berat_pesanan_kg=item['berat'],
                        harga_per_kg=item['harga_per_kg'],
                        subtotal_item=item['subtotal']
                    )

                # Create PembayaranDaging
                PembayaranDaging.objects.create(
                    pesanan=pesanan,
                    tagihan=total_tagihan,
                    menunggu_persetujuan=0,
                    sudah_dibayar=0
                )

                return Response(PesananDagingSerializer(pesanan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        PBI-28 : Update Status Pesanan Mazdaging
        """
        instance = self.get_object_or_404_by_id(kwargs.get('pk'))
        
        # PBI-28: Jika pesanan sudah berstatus Selesai atau Dibatalkan → return 400
        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Diproses', 'Selesai', 'Dibatalkan']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # Transition validation: Diproses → Selesai OR Diproses → Dibatalkan
        if instance.status_pesanan != 'Diproses' and new_status != instance.status_pesanan:
             return Response({"detail": "Transisi status tidak diperbolehkan."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = catatan
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                
                if new_status == 'Selesai':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar = pembayaran.tagihan
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()

                instance.save()
                return Response(PesananDagingSerializer(instance).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_object_or_404_by_id(self, pk):
        try:
            return PesananDaging.objects.get(pk=pk, deleted_at__isnull=True)
        except PesananDaging.DoesNotExist:
            from django.http import Http404
            raise Http404("Pesanan tidak ditemukan.")


class OrderInvestViewSet(viewsets.ModelViewSet):
    """
    Manajemen Pesanan Invest Ternak
    POST   /api/sales/order/invest/         → Create order
    GET    /api/sales/order/invest/         → List orders (filter, pagination)
    PUT    /api/sales/order/invest/{pk}/    → Update status
    """
    queryset = PesananInvest.objects.filter(deleted_at__isnull=True)
    serializer_class = PesananInvestSerializer
    permission_classes = [IsSuperAdminOrMarketing]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'customer', 'pembayaran'
        ).prefetch_related(
            'items__invest'
        )
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = OrderInvestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        id_customer = serializer.validated_data['id_customer']
        daftar_id_invest = serializer.validated_data['items']
        catatan = serializer.validated_data.get('catatan', '')

        try:
            customer = User.objects.get(id=id_customer)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                invests = []
                total_tagihan = 0
                for iid in daftar_id_invest:
                    try:
                        invest = Invest.objects.select_for_update().get(id_invest=iid)
                    except Invest.DoesNotExist:
                        return Response({"detail": f"Invest {iid} tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

                    if invest.deleted_at is not None:
                        return Response({"detail": f"Invest {iid} tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

                    if invest.status_investernak != 'Open':
                        return Response(
                            {"detail": f"Invest {iid} tidak tersedia (status: {invest.status_investernak})."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    invests.append(invest)
                    total_tagihan += invest.harga_sapi

                pesanan = PesananInvest.objects.create(
                    customer=customer,
                    catatan=catatan,
                    status_pesanan='Diproses',
                    updated_at=None,
                )

                for invest in invests:
                    OrderItemInvest.objects.create(
                        pesanan=pesanan,
                        invest=invest,
                        harga_sapi=invest.harga_sapi,
                    )
                    invest.status_investernak = 'Ongoing'
                    invest.save()

                PembayaranInvest.objects.create(
                    pesanan=pesanan,
                    tagihan=total_tagihan,
                    menunggu_persetujuan=0,
                    sudah_dibayar=0,
                )

                return Response(PesananInvestSerializer(pesanan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self._get_pesanan_or_404(kwargs.get('pk'))

        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response(
                {"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Diproses', 'Selesai', 'Dibatalkan']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        if instance.status_pesanan != 'Diproses' and new_status != instance.status_pesanan:
            return Response({"detail": "Transisi status tidak diperbolehkan."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = catatan
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                instance.save()

                items = instance.items.all()
                if new_status == 'Selesai':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar = pembayaran.tagihan
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    for item in items:
                        item.invest.status_investernak = 'Closed'
                        item.invest.save()
                elif new_status == 'Dibatalkan':
                    for item in items:
                        item.invest.status_investernak = 'Open'
                        item.invest.save()

                return Response(PesananInvestSerializer(instance).data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_pesanan_or_404(self, pk):
        try:
            return PesananInvest.objects.get(pk=pk, deleted_at__isnull=True)
        except PesananInvest.DoesNotExist:
            from django.http import Http404
            raise Http404("Pesanan tidak ditemukan.")