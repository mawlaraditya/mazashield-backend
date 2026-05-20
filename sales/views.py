from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Pesanan, OrderItem, Pembayaran, 
    PesananDaging, OrderItemDaging, PembayaranDaging, 
    PesananInvest, OrderItemInvest, PembayaranInvest,
    RiwayatPembayaran
)
from .serializers import (
    PesananSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    PesananDagingSerializer, OrderDagingCreateSerializer,
    PesananInvestSerializer, OrderInvestCreateSerializer, OrderInvestUpdateSerializer,
    RiwayatPembayaranSerializer,
    CustomerPesananMazdafarmSerializer, CustomerPesananMazdagingSerializer,
)
from accounts.models import User
from catalogs.models import Ternak, Daging, Invest
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Q, Sum, Count
from rest_framework.views import APIView
from django.contrib.contenttypes.models import ContentType
import decimal
from rest_framework.pagination import PageNumberPagination
from django.db.models.functions import TruncMonth

class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100

class IsSuperAdminOrMarketing(permissions.BasePermission):
    def has_permission(self, request, view):
        # CEO and Komisaris can only read (GET). Marketing and SuperAdmin can do anything.
        if request.user.is_authenticated:
            if request.user.role in ['SuperAdmin', 'Marketing']:
                return True
            if request.user.role in ['CEO', 'Komisaris'] and request.method in permissions.SAFE_METHODS:
                return True
        return False



class IsFinance(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['Finance', 'SuperAdmin']

class OrderMazdafarmViewSet(viewsets.ModelViewSet):
    """
    Manajemen Pesanan Mazdafarm
    """
    queryset = Pesanan.objects.filter(deleted_at__isnull=True)
    serializer_class = PesananSerializer
    permission_classes = [IsSuperAdminOrMarketing]
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        PBI-25: Read Internal Mazdafarm (Filter by status & created_at range)
        Optimized with select_related and prefetch_related
        """
        queryset = super().get_queryset().select_related(
            'customer', 'pembayaran'
        ).prefetch_related(
            'items__ternak',
            'payment_logs__created_by',
            'payment_logs__verified_by'
        )
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
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
        ongkir = serializer.validated_data.get('ongkir', 0)

        # PBI-23: Jika customer tidak ditemukan → return 404 Not Found
        try:
            customer = User.objects.get(id=id_customer)
            if customer.role != 'Customer':
                return Response({"detail": "User yang dipilih bukan merupakan customer."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)


        try:
            with transaction.atomic():
                # PBI-23: Bulk validate cattle availability
                ternaks_qs = Ternak.objects.select_for_update().filter(
                    id_ternak__in=daftar_id_ternak, 
                    deleted_at__isnull=True
                )
                
                # Create a map for quick lookup and maintain order if needed
                ternak_map = {t.id_ternak: t for t in ternaks_qs}
                ternaks = []
                total_tagihan = Decimal('0')
                
                for tid in daftar_id_ternak:
                    ternak = ternak_map.get(tid)
                    if not ternak:
                        return Response({"detail": f"Ternak {tid} tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
                    if ternak.status_ternak != 'Available':
                        return Response({"detail": f"Ternak {tid} tidak tersedia."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    ternaks.append(ternak)
                    total_tagihan += ternak.harga

                # Create Pesanan
                pesanan = Pesanan.objects.create(
                    customer=customer,
                    catatan=catatan,
                    ongkir=ongkir,
                    status_pesanan='Processed',
                    updated_at=timezone.now()
                )


                # Optimized: Bulk create OrderItems
                order_items = [
                    OrderItem(
                        pesanan=pesanan,
                        ternak=ternak,
                        berat_pesanan_kg=1.00,
                        harga=ternak.harga
                    ) for ternak in ternaks
                ]
                OrderItem.objects.bulk_create(order_items)

                # Optimized: Bulk update Ternak status
                for ternak in ternaks:
                    ternak.status_ternak = 'Booked'
                Ternak.objects.bulk_update(ternaks, ['status_ternak'])

                # Create Pembayaran
                Pembayaran.objects.create(
                    pesanan=pesanan,
                    tagihan=total_tagihan + Decimal(str(ongkir)),
                    menunggu_persetujuan=0,
                    sudah_dibayar=0
                )

                return Response(PesananSerializer(pesanan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):

        """
        PBI-28: Update Status Pesanan Mazdafarm (Strict Validation)
        """
        instance = self.get_object_or_404_by_id(kwargs.get('pk'))
        
        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Completed', 'Cancelled']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)
        
        # 2. Status validity
        if new_status not in ['Processed', 'Completed', 'Cancelled']:
             return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Payment Validation for Selesai
        if new_status == 'Completed':
            pembayaran = instance.pembayaran
            if pembayaran.tagihan > 0 or pembayaran.menunggu_persetujuan > 0:
                return Response({"detail": "Status tidak bisa diubah ke Selesai: Masih ada sisa tagihan atau pembayaran menunggu verifikasi finance."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = catatan
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                
                # Sync stock and payment logs
                items = instance.items.all()
                if new_status == 'Completed':
                    # Fill payment data (though strictly should be 0 remainder already)
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    # Optimized: Bulk update Ternak status
                    for item in items:
                        item.ternak.status_ternak = 'Sold'
                    Ternak.objects.bulk_update([item.ternak for item in items], ['status_ternak'])
                elif new_status == 'Cancelled':
                    # Optimized: Bulk update Ternak status
                    for item in items:
                        item.ternak.status_ternak = 'Available'
                    Ternak.objects.bulk_update([item.ternak for item in items], ['status_ternak'])
                    
                    # Reset payment expectations
                    pembayaran = instance.pembayaran
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()

                instance.save()
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
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


    def get_queryset(self):
        """
        PBI-29: Read Internal Mazdaging (Filter by status & created_at range)
        Optimized with select_related and prefetch_related
        """
        queryset = super().get_queryset().select_related(
            'customer', 'pembayaran'
        ).prefetch_related(
            'items__daging',
            'payment_logs__created_by',
            'payment_logs__verified_by'
        )
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
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
        ongkir = serializer.validated_data.get('ongkir', 0)

        try:
            customer = User.objects.get(id=id_customer)
            if customer.role != 'Customer':
                return Response({"detail": "User yang dipilih bukan merupakan customer."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)


        try:
            with transaction.atomic():
                # PBI-27: Bulk validate meat availability
                id_dagings = [item['id_daging'] for item in items_data]
                dagings_qs = Daging.objects.select_for_update().filter(
                    id_daging__in=id_dagings,
                    deleted_at__isnull=True
                )
                daging_map = {d.id_daging: d for d in dagings_qs}
                
                items_to_create = []
                total_tagihan = Decimal('0')
                for item_data in items_data:
                    id_daging = item_data['id_daging']
                    berat_pesanan_kg = Decimal(str(item_data['berat_pesanan_kg']))
                    daging = daging_map.get(id_daging)
                    
                    if not daging:
                        return Response({"detail": f"Daging {id_daging} tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    if daging.status_daging not in ['Tersedia', 'Pre Order']:
                        return Response({"detail": f"Daging {id_daging} tidak tersedia."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    subtotal = daging.harga_per_kg * berat_pesanan_kg
                    items_to_create.append({
                        'daging': daging,
                        'berat': berat_pesanan_kg,
                        'harga_per_kg': daging.harga_per_kg,
                        'subtotal': subtotal
                    })
                    total_tagihan += subtotal

                # Create PesananDaging
                pesanan = PesananDaging.objects.create(
                    customer=customer,
                    catatan=catatan,
                    ongkir=ongkir,
                    status_pesanan='Processed',
                    updated_at=timezone.now()
                )


                # Optimized: Bulk create OrderItems
                order_items = [
                    OrderItemDaging(
                        pesanan=pesanan,
                        daging=item['daging'],
                        berat_pesanan_kg=item['berat'],
                        harga_per_kg=item['harga_per_kg'],
                        subtotal_item=item['subtotal']
                    ) for item in items_to_create
                ]
                OrderItemDaging.objects.bulk_create(order_items)

                # Update status if needed (Daging doesn't always lock but let's be consistent)
                # No bulk update needed for Daging here as it's not strictly 'Dipesan' in PBI logic

                # Create PembayaranDaging
                PembayaranDaging.objects.create(
                    pesanan=pesanan,
                    tagihan=total_tagihan + Decimal(str(ongkir)),
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
        
        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Completed', 'Cancelled']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Processed', 'Completed', 'Cancelled']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Payment Validation for Selesai
        if new_status == 'Completed':
            pembayaran = instance.pembayaran
            if pembayaran.tagihan > 0 or pembayaran.menunggu_persetujuan > 0:
                return Response({"detail": "Status tidak bisa diubah ke Selesai: Masih ada sisa tagihan atau pembayaran menunggu verifikasi finance."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = catatan
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                
                items = instance.items.all()
                if new_status == 'Completed':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    # Stock logic for Daging (Optimized bulk update)
                    for item in items:
                        item.daging.status_daging = 'Terjual'
                    Daging.objects.bulk_update([item.daging for item in items], ['status_daging'])
                elif new_status == 'Cancelled':
                    for item in items:
                        item.daging.status_daging = 'Tersedia'
                    Daging.objects.bulk_update([item.daging for item in items], ['status_daging'])

                    # Reset payment expectations
                    pembayaran = instance.pembayaran
                    pembayaran.tagihan = 0
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
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status_pesanan']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'customer', 'pembayaran'
        ).prefetch_related(
            'items__invest',
            'payment_logs__created_by',
            'payment_logs__verified_by'
        )
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
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
            if customer.role != 'Customer':
                return Response({"detail": "User yang dipilih bukan merupakan customer."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail": "Customer tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)


        try:
            with transaction.atomic():
                invests_qs = Invest.objects.select_for_update().filter(
                    id_invest__in=daftar_id_invest,
                    deleted_at__isnull=True
                )
                invest_map = {i.id_invest: i for i in invests_qs}

                invests = []
                total_tagihan = 0
                for iid in daftar_id_invest:
                    invest = invest_map.get(iid)
                    if not invest:
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
                    status_pesanan='Processed',
                    updated_at=timezone.now(),
                )


                # Optimized: Bulk create OrderItems
                order_items = [
                    OrderItemInvest(
                        pesanan=pesanan,
                        invest=invest,
                        harga_sapi=invest.harga_sapi,
                    ) for invest in invests
                ]
                OrderItemInvest.objects.bulk_create(order_items)

                # Optimized: Bulk update Invest status
                for invest in invests:
                    invest.status_investernak = 'Ongoing'
                Invest.objects.bulk_update(invests, ['status_investernak'])

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
        """
        PBI-28: Update Status Pesanan Invest Ternak
        """
        instance = self._get_pesanan_or_404(kwargs.get('pk'))

        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Completed', 'Cancelled']:
            return Response(
                {"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Processed', 'Completed', 'Cancelled']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Payment Validation for Selesai
        if new_status == 'Completed':
            pembayaran = instance.pembayaran
            if pembayaran.tagihan > 0 or pembayaran.menunggu_persetujuan > 0:
                return Response({"detail": "Status tidak bisa diubah ke Selesai: Masih ada sisa tagihan atau pembayaran menunggu verifikasi finance."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                instance.status_pesanan = new_status
                instance.catatan = catatan
                instance.updated_at = timezone.now()
                instance.updated_by = request.user
                
                items = instance.items.all()
                if new_status == 'Completed':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    # Optimized: Bulk update Invest status
                    for item in items:
                        item.invest.status_investernak = 'Closed'
                    Invest.objects.bulk_update([item.invest for item in items], ['status_investernak'])
                elif new_status == 'Cancelled':
                    for item in items:
                        item.invest.status_investernak = 'Open'
                    Invest.objects.bulk_update([item.invest for item in items], ['status_investernak'])

                    # Reset payment expectations
                    pembayaran = instance.pembayaran
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()

                instance.save()
                return Response(PesananInvestSerializer(instance).data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_pesanan_or_404(self, pk):
        try:
            return PesananInvest.objects.get(pk=pk, deleted_at__isnull=True)
        except PesananInvest.DoesNotExist:
            from django.http import Http404
            raise Http404("Pesanan tidak ditemukan.")

# ── PAYMENT MANAGEMENT (PBI-35, PBI-36) ───────────────────────────────────

class PaymentUpdateView(APIView):
    permission_classes = [IsSuperAdminOrMarketing]

    def put(self, request, id_pesanan):
        # 1. Validate mandatory fields
        required_fields = ['nominal_pembayaran', 'bank_pengirim', 'nomor_rekening_pengirim', 'tanggal_transfer', 'waktu_transfer']
        for field in required_fields:
            if field not in request.data:
                return Response({"detail": f"Field {field} wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nominal = decimal.Decimal(str(request.data['nominal_pembayaran']))
        except (ValueError, decimal.InvalidOperation):
            return Response({"detail": "Nominal pembayaran tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        if nominal <= 0:
            return Response({"detail": "Nominal pembayaran wajib > 0."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Find order and associated pembayaran
        order_type_str = request.data.get('order_type')
        if not order_type_str:
            return Response({"detail": "Field order_type wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        order = None
        pembayaran = None
        content_type = None

        model_map = {
            'pesananternak': (Pesanan, 'pembayaran'),
            'pesananinvest': (PesananInvest, 'pembayaran'),
            'pesanandaging': (PesananDaging, 'pembayaran')
        }





        if order_type_str not in model_map:
             return Response({"detail": "order_type tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        model, rel_name = model_map[order_type_str]

        try:
            obj = model.objects.get(pk=id_pesanan, deleted_at__isnull=True)
            if hasattr(obj, rel_name):
                order = obj
                pembayaran = getattr(obj, rel_name)
                content_type = ContentType.objects.get_for_model(model)
        except model.DoesNotExist:
            pass


        if not order:
            return Response({"detail": "Pesanan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # 3. Validate order status
        if order.status_pesanan == 'Cancelled':
            return Response({"detail": "Pesanan sudah dibatalkan."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Validate nominal <= tagihan
        if nominal > pembayaran.tagihan:
            return Response({"detail": "Nominal melebihi sisa tagihan."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Sanitization: Ensure account number is only digits
                nomor_rek = "".join(filter(str.isdigit, str(request.data['nomor_rekening_pengirim'])))

                # 5. Create RiwayatPembayaran
                riwayat = RiwayatPembayaran.objects.create(
                    content_type=content_type,
                    object_id=order.id,
                    nominal_pembayaran=nominal,
                    bank_pengirim=request.data['bank_pengirim'],
                    nomor_rekening_pengirim=nomor_rek,
                    nama_pengirim=request.data.get('nama_pengirim', ''),
                    tanggal_transfer=request.data['tanggal_transfer'],
                    waktu_transfer=request.data['waktu_transfer'],
                    catatan=request.data.get('catatan', ''),
                    status='Waiting',
                    created_by=request.user
                )

                # 6. Update Pembayaran fields
                pembayaran.menunggu_persetujuan += nominal
                pembayaran.tagihan -= nominal
                pembayaran.save()

                return Response({"detail": "Pembayaran berhasil diinput."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PaymentVerifyView(APIView):
    permission_classes = [IsFinance]

    def put(self, request, payment_id):
        # 1. Find RiwayatPembayaran
        try:
            riwayat = RiwayatPembayaran.objects.get(pk=payment_id)
        except RiwayatPembayaran.DoesNotExist:
            return Response({"detail": "Data pembayaran tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if riwayat.status != 'Waiting':
            return Response({"detail": "Pembayaran ini sudah diverifikasi."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Validate decisions
        keputusan = request.data.get('keputusan')
        if keputusan not in ['Paid', 'Unpaid']:
            return Response({"detail": "Keputusan wajib Diterima atau Ditolak."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Get associated pembayaran
        order = riwayat.content_object
        pembayaran = order.pembayaran

        # 4. Mandatory validation: menunggu_persetujuan must have sufficient funds
        if pembayaran.menunggu_persetujuan < riwayat.nominal_pembayaran:
            return Response({
                "detail": f"Data data finansial tidak sinkron: Menunggu persetujuan (Rp {pembayaran.menunggu_persetujuan}) "
                          f"kurang dari nominal verifikasi (Rp {riwayat.nominal_pembayaran})."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if keputusan == 'Paid':
                    pembayaran.sudah_dibayar += riwayat.nominal_pembayaran
                    pembayaran.menunggu_persetujuan -= riwayat.nominal_pembayaran
                    riwayat.status = 'Paid'
                    
                    # Logic: If tagihan is 0, this order is effectively fully paid (ready to be Selesai)
                    ready_to_complete = (pembayaran.tagihan == 0 and pembayaran.menunggu_persetujuan == 0)
                else:
                    pembayaran.tagihan += riwayat.nominal_pembayaran
                    pembayaran.menunggu_persetujuan -= riwayat.nominal_pembayaran
                    riwayat.status = 'Unpaid'
                    ready_to_complete = False
                
                pembayaran.save()
                
                riwayat.verified_at = timezone.now()
                riwayat.verified_by = request.user
                riwayat.catatan_verifikasi = request.data.get('catatan_verifikasi', '')
                riwayat.save()

                detail_msg = f"Pembayaran berhasil {keputusan}."
                if ready_to_complete:
                    detail_msg += " Pesanan ini sekarang telah lunas dan siap untuk diselesaikan."

                return Response({"detail": detail_msg, "ready_to_complete": ready_to_complete}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RiwayatPembayaranViewSet(viewsets.ReadOnlyModelViewSet):
    """
    PBI-36: Finance monitoring payment log
    Optimized with select_related to avoid N+1 on users and prefetch_related for content_object
    """
    queryset = RiwayatPembayaran.objects.all().select_related(
        'created_by', 'verified_by'
    ).prefetch_related(
        'content_object',
        'content_object__customer'  # Optimized: Prefetch customer on content_object
    ).order_by('-created_at')
    serializer_class = RiwayatPembayaranSerializer
    permission_classes = [IsFinance]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        if status_filter:
            return self.queryset.filter(status=status_filter)
        return self.queryset


# ── PBI-40: FINANCIAL DASHBOARD ───────────────────────────────────────────────

class IsSuperAdminOrFinance(permissions.BasePermission):
    """PBI-40: Only SuperAdmin and Finance (Direktur Keuangan) may access the financial dashboard."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ['SuperAdmin', 'Finance']
        )


class FinancialDashboardView(APIView):
    """
    PBI-40: Dashboard Finansial
    GET /api/finance/dashboard/?tahun=<yyyy>
    Returns:
      - total_pendapatan_keseluruhan  : sum of sudah_dibayar from all completed orders
      - data_penjualan_per_bulan      : list of {bulan, total_penjualan} for the given year
      - data_customer_baru_per_bulan  : list of {bulan, jumlah_customer} for the given year
    """
    permission_classes = [IsSuperAdminOrFinance]

    def get(self, request):
        tahun = request.query_params.get('tahun')
        try:
            tahun = int(tahun) if tahun else timezone.now().year
        except (ValueError, TypeError):
            return Response({"detail": "Parameter tahun tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        MONTH_NAMES = ['','Januari','Februari','Maret','April','Mei','Juni',
                       'Juli','Agustus','September','Oktober','November','Desember']

        Z = decimal.Decimal('0')

        # ── helpers ─────────────────────────────────────────────────────────
        def _sum_done(model, rel):
            return float(model.objects.filter(status_pesanan='Completed', deleted_at__isnull=True)
                         .aggregate(t=Sum(f'{rel}__sudah_dibayar'))['t'] or Z)

        def _sum_done_year(model, rel):
            return float(model.objects.filter(status_pesanan='Completed', deleted_at__isnull=True, created_at__year=tahun)
                         .aggregate(t=Sum(f'{rel}__sudah_dibayar'))['t'] or Z)

        def _monthly(model, rel):
            return (model.objects
                    .filter(status_pesanan='Completed', deleted_at__isnull=True, created_at__year=tahun)
                    .annotate(bulan=TruncMonth('created_at')).values('bulan')
                    .annotate(total=Sum(f'{rel}__sudah_dibayar')).order_by('bulan'))

        def _piutang(model, rel):
            agg = (model.objects.filter(status_pesanan='Processed', deleted_at__isnull=True)
                   .aggregate(tagihan=Sum(f'{rel}__tagihan'), menunggu=Sum(f'{rel}__menunggu_persetujuan')))
            return {"tagihan": float(agg['tagihan'] or Z), "menunggu_verifikasi": float(agg['menunggu'] or Z)}

        # ── 1. Total Penjualan Tahun Aktif (PBI-39 equivalent) ───────────────────
        mf_year = _sum_done_year(Pesanan,       'pembayaran')
        mg_year = _sum_done_year(PesananDaging, 'pembayaran')
        iv_year = _sum_done_year(PesananInvest, 'pembayaran')
        total_penjualan_tahun_aktif = mf_year + mg_year + iv_year

        # ── 2. Penjualan Per Bulan ─────────────────────────────────────────────
        monthly_map = {}
        
        for name, qs in [('mazdafarm', _monthly(Pesanan,'pembayaran')), 
                         ('mazdaging', _monthly(PesananDaging,'pembayaran')), 
                         ('investernak', _monthly(PesananInvest,'pembayaran'))]:
            for row in qs:
                m = row['bulan'].month
                if m not in monthly_map:
                    monthly_map[m] = {'total': Z, 'mazdafarm': Z, 'mazdaging': Z, 'investernak': Z}
                
                val = row['total'] or Z
                monthly_map[m][name] += val
                monthly_map[m]['total'] += val

        penjualan_per_bulan = [
            {
                "bulan": MONTH_NAMES[m], 
                "total": float(monthly_map.get(m, {}).get('total', Z)),
                "mazdafarm": float(monthly_map.get(m, {}).get('mazdafarm', Z)),
                "mazdaging": float(monthly_map.get(m, {}).get('mazdaging', Z)),
                "investernak": float(monthly_map.get(m, {}).get('investernak', Z))
            }
            for m in range(1, 13)
        ]

        # ── 3. Customer Baru Per Bulan ─────────────────────────────────────────
        customer_qs = (User.objects.filter(role='Customer', deleted_at__isnull=True, created_at__year=tahun)
                       .annotate(bulan=TruncMonth('created_at')).values('bulan')
                       .annotate(jumlah=Count('id')).order_by('bulan'))
        cust_map = {r['bulan'].month: r['jumlah'] for r in customer_qs}
        customer_baru_per_bulan = [
            {"bulan": MONTH_NAMES[m], "jumlah": cust_map.get(m, 0)}
            for m in range(1, 13)
        ]
        total_customer_baru = sum(c['jumlah'] for c in customer_baru_per_bulan)

        # ── 4. Breakdown Per Layanan ───────────────────────────────────────────
        def calc_pct(val, total):
            return float((val / total) * 100) if total > 0 else 0.0

        breakdown_per_layanan = [
            {"layanan": "Mazdafarm", "total": mf_year, "persentase": calc_pct(mf_year, total_penjualan_tahun_aktif)},
            {"layanan": "Mazdaging", "total": mg_year, "persentase": calc_pct(mg_year, total_penjualan_tahun_aktif)},
            {"layanan": "Investernak", "total": iv_year, "persentase": calc_pct(iv_year, total_penjualan_tahun_aktif)},
        ]

        # ── 5. Piutang Aktif (Pesanan Diproses) ────────────────────────────────
        pf = _piutang(Pesanan,       'pembayaran')
        pg = _piutang(PesananDaging, 'pembayaran')
        pi = _piutang(PesananInvest, 'pembayaran')

        total_belum_bayar = pf["tagihan"] + pg["tagihan"] + pi["tagihan"]
        total_menunggu_verif = pf["menunggu_verifikasi"] + pg["menunggu_verifikasi"] + pi["menunggu_verifikasi"]

        piutang_per_layanan = [
            {"layanan": "Mazdafarm", "belum_bayar": pf["tagihan"], "menunggu_verif": pf["menunggu_verifikasi"]},
            {"layanan": "Mazdaging", "belum_bayar": pg["tagihan"], "menunggu_verif": pg["menunggu_verifikasi"]},
            {"layanan": "Investernak", "belum_bayar": pi["tagihan"], "menunggu_verif": pi["menunggu_verifikasi"]},
        ]

        return Response({
            "filter_tahun": tahun,
            "total_penjualan_tahun_aktif": total_penjualan_tahun_aktif,
            "total_piutang": { "belum_bayar": total_belum_bayar, "menunggu_verif": total_menunggu_verif },
            "total_customer_baru": total_customer_baru,
            "penjualan_per_bulan": penjualan_per_bulan,
            "customer_baru_per_bulan": customer_baru_per_bulan,
            "breakdown_per_layanan": breakdown_per_layanan,
            "piutang_per_layanan": piutang_per_layanan
        }, status=status.HTTP_200_OK)
# ── CUSTOMER-FACING VIEWS (Read-Only, External) ────────────────────────────

class IsCustomer(permissions.BasePermission):
    """Customer yang sudah login dan aktif."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'Customer' and
            request.user.deleted_at is None
        )


class CustomerOrderMazdafarmView(APIView):
    """
    PBI-External-1: Read Order Mazdafarm untuk Customer.
    GET /api/order/mazdafarm        → list semua pesanan milik customer yang login
    GET /api/order/mazdafarm/<pk>   → detail satu pesanan milik customer yang login
    Hanya bisa READ. Tidak ada create/update/delete.
    """
    permission_classes = [IsCustomer]

    def _get_base_queryset(self, user):
        return (
            Pesanan.objects
            .filter(customer=user, deleted_at__isnull=True)
            .select_related('pembayaran')
            .prefetch_related('items__ternak')
            .order_by('-created_at')
        )

    def get(self, request, pk=None):
        if pk is not None:
            # Detail view
            try:
                pesanan = self._get_base_queryset(request.user).get(pk=pk)
            except Pesanan.DoesNotExist:
                return Response(
                    {"detail": "Pesanan tidak ditemukan."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = CustomerPesananMazdafarmSerializer(
                pesanan, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        # List view dengan pagination
        queryset = self._get_base_queryset(request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status_pesanan=status_filter)

        paginator = OrderPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CustomerPesananMazdafarmSerializer(
            page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)


class CustomerOrderMazdagingView(APIView):
    """
    PBI-External-2: Read Order Mazdaging untuk Customer.
    GET /api/order/mazdaging        → list semua order milik customer yang login
    GET /api/order/mazdaging/<pk>   → detail satu order milik customer yang login
    Hanya bisa READ. Tidak ada create/update/delete.
    """
    permission_classes = [IsCustomer]

    def _get_base_queryset(self, user):
        return (
            PesananDaging.objects
            .filter(customer=user, deleted_at__isnull=True)
            .select_related('pembayaran')
            .prefetch_related('items__daging')
            .order_by('-created_at')
        )

    def get(self, request, pk=None):
        if pk is not None:
            # Detail view
            try:
                pesanan = self._get_base_queryset(request.user).get(pk=pk)
            except PesananDaging.DoesNotExist:
                return Response(
                    {"detail": "Order tidak ditemukan."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = CustomerPesananMazdagingSerializer(
                pesanan, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        # List view dengan pagination
        queryset = self._get_base_queryset(request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status_pesanan=status_filter)

        paginator = OrderPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CustomerPesananMazdagingSerializer(
            page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)



# ── PBI-37: Update Laporan Hasil Investasi (Marketing/SuperAdmin) ─────────────

class LaporanInvestasiView(APIView):
    """
    PBI-37: Manage investment report for a given PesananInvest.
    GET  /api/sales/laporan-invest/<id_pesanan>/ -> Return current laporan (auto-creates one if missing)
    Access: SuperAdmin and Marketing only.
    """
    permission_classes = [IsSuperAdminOrMarketing]

    def _get_pesanan(self, id_pesanan):
        try:
            return PesananInvest.objects.select_related('pembayaran').get(
                pk=id_pesanan, deleted_at__isnull=True
            )
        except PesananInvest.DoesNotExist:
            return None

    def get(self, request, id_pesanan):
        pesanan = self._get_pesanan(id_pesanan)
        if not pesanan:
            return Response({"detail": "Pesanan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        from .models import LaporanInvestasi
        laporan, _ = LaporanInvestasi.objects.get_or_create(pesanan=pesanan)
        from .serializers import LaporanInvestasiSerializer
        return Response(LaporanInvestasiSerializer(laporan).data, status=status.HTTP_200_OK)


class LaporanInvestasiBeratView(APIView):
    """
    PBI-37: POST /api/sales/laporan-invest/<id_pesanan>/berat/
    Add a new weekly weight entry (only when status_pesanan = Diproses).
    """
    permission_classes = [IsSuperAdminOrMarketing]

    def post(self, request, id_pesanan):
        from .models import LaporanInvestasi, HistoriBerat
        from .serializers import HistoriBeratInputSerializer, LaporanInvestasiSerializer
        try:
            pesanan = PesananInvest.objects.select_related('pembayaran').get(pk=id_pesanan, deleted_at__isnull=True)
        except PesananInvest.DoesNotExist:
            return Response({"detail": "Pesanan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if pesanan.status_pesanan not in ['Processed']:
            return Response({"detail": "Input berat mingguan hanya tersedia selama status pesanan = Processed."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HistoriBeratInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        laporan, _ = LaporanInvestasi.objects.get_or_create(pesanan=pesanan)

        if 'harga_jual_per_kg' in request.data:
            try:
                import decimal
                laporan.harga_jual_per_kg = decimal.Decimal(str(request.data['harga_jual_per_kg']))
            except Exception: pass
        if 'target_berat_kg' in request.data:
            try:
                import decimal
                laporan.target_berat_kg = decimal.Decimal(str(request.data['target_berat_kg']))
            except Exception: pass
        laporan.save()


        HistoriBerat.objects.create(
            laporan=laporan,
            tanggal_input=serializer.validated_data['tanggal_input'],
            berat_kg=serializer.validated_data['berat_kg'],
            keterangan=serializer.validated_data.get('keterangan', ''),
        )
        return Response(LaporanInvestasiSerializer(laporan).data, status=status.HTTP_200_OK)


class LaporanInvestasiAkhirView(APIView):
    """
    PBI-37: PUT /api/sales/laporan-invest/<id_pesanan>/akhir/
    Save final calculation (only when status_pesanan = Selesai).
    """
    permission_classes = [IsSuperAdminOrMarketing]

    def put(self, request, id_pesanan):
        from .models import LaporanInvestasi
        from .serializers import PerhitunganAkhirSerializer, LaporanInvestasiSerializer
        try:
            pesanan = PesananInvest.objects.select_related('pembayaran').get(pk=id_pesanan, deleted_at__isnull=True)
        except PesananInvest.DoesNotExist:
            return Response({"detail": "Pesanan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if pesanan.status_pesanan != 'Completed':
            return Response({"detail": "Perhitungan akhir hanya dapat disimpan ketika status pesanan = Selesai."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PerhitunganAkhirSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        laporan, _ = LaporanInvestasi.objects.get_or_create(pesanan=pesanan)
        for field in ['harga_jual_aktual', 'biaya_pakan', 'biaya_operasional', 'biaya_obat_vitamin', 'fee_marketing']:
            setattr(laporan, field, serializer.validated_data[field])
        laporan.hitung_akhir()
        laporan.save()
        return Response(LaporanInvestasiSerializer(laporan).data, status=status.HTTP_200_OK)


# ── PBI-38: Read Laporan Hasil Investasi (Customer) ───────────────────────────

class LaporanInvestasiCustomerView(APIView):
    """
    PBI-38: GET /api/order/invest/<id_pesanan>/laporan/
    Customer reads their own investment report (read-only).
    """
    permission_classes = [IsCustomer]

    def get(self, request, id_pesanan):
        from .models import LaporanInvestasi
        from .serializers import LaporanInvestasiSerializer
        try:
            pesanan = PesananInvest.objects.select_related('pembayaran').get(
                pk=id_pesanan, deleted_at__isnull=True, customer=request.user
            )
        except PesananInvest.DoesNotExist:
            return Response({"detail": "Pesanan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if pesanan.status_pesanan == 'Cancelled':
            return Response({
                "id_pesanan": pesanan.formatted_id_pesanan,
                "status_pesanan": "Cancelled",
                "detail": "Investasi ini telah dibatalkan. Tidak ada laporan hasil yang tersedia.",
            }, status=status.HTTP_200_OK)

        laporan, _ = LaporanInvestasi.objects.get_or_create(pesanan=pesanan)
        return Response(LaporanInvestasiSerializer(laporan).data, status=status.HTTP_200_OK)


# ── PBI-34: Read Order Invest External (Customer) ─────────────────────────────

class OrderInvestExternalView(APIView):
    """
    PBI-34: GET /api/order/invest/
    Returns all PesananInvest belonging to the logged-in customer.
    """
    permission_classes = [IsCustomer]

    def get(self, request):
        from .serializers import PesananInvestExternalSerializer
        queryset = (
            PesananInvest.objects
            .filter(customer=request.user, deleted_at__isnull=True)
            .select_related('pembayaran')
            .prefetch_related('items__invest')
            .order_by('-created_at')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status_pesanan=status_filter)
            
        serializer = PesananInvestExternalSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ── PBI-39: Laporan Penjualan (Marketing/SuperAdmin) ──────────────────────────


class LaporanPenjualanView(APIView):
    """
    PBI-39: GET /api/sales/laporan-penjualan/
    Returns all completed orders (status = Selesai) across all 3 order types.
    Supports filters: start_date, end_date, jenis_layanan.
    Returns rekapitulasi: total_transaksi, total_customer_unik, total_pendapatan.
    Supports pagination via ?page=&limit= query params.
    """
    permission_classes = [IsSuperAdminOrMarketing]

    def get(self, request):
        start_date    = request.query_params.get('start_date')
        end_date      = request.query_params.get('end_date')
        jenis_layanan = request.query_params.get('jenis_layanan')  # Mazdafarm | Mazdaging | Investernak
        page          = int(request.query_params.get('page', 1))
        limit         = min(int(request.query_params.get('limit', 10)), 100)

        orders = []

        def _add_orders(model, payment_rel, jenis, label):
            qs = model.objects.filter(status_pesanan='Completed', deleted_at__isnull=True)
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)
            qs = qs.select_related('customer', payment_rel)
            for o in qs:
                payment = getattr(o, payment_rel)
                orders.append({
                    'id_pesanan':           o.formatted_id_pesanan,
                    'nama_customer':        o.customer.nama,
                    'jenis_layanan':        jenis,
                    # Untuk pesanan selesai, tagihan = 0, jadi total asli = sudah_dibayar + tagihan + menunggu_persetujuan
                    'total_tagihan':        float(payment.sudah_dibayar) + float(payment.tagihan) + float(payment.menunggu_persetujuan),
                    'sudah_dibayar':        float(payment.sudah_dibayar),
                    'menunggu_persetujuan': float(payment.menunggu_persetujuan),
                    'tanggal_transaksi':    o.created_at,
                })

        if not jenis_layanan or jenis_layanan == 'Mazdafarm':
            _add_orders(Pesanan,       'pembayaran', 'Mazdafarm',   'Pesanan Ternak')
        if not jenis_layanan or jenis_layanan == 'Mazdaging':
            _add_orders(PesananDaging, 'pembayaran', 'Mazdaging',   'Pesanan Daging')
        if not jenis_layanan or jenis_layanan == 'Investernak':
            _add_orders(PesananInvest, 'pembayaran', 'Investernak', 'Pesanan Invest Ternak')

        # Sort by date descending
        orders.sort(key=lambda x: x['tanggal_transaksi'], reverse=True)

        # Rekapitulasi
        total_pendapatan    = sum(o['total_tagihan'] for o in orders)
        customer_unik       = len(set(o['nama_customer'] for o in orders))
        total_transaksi     = len(orders)

        # Pagination
        offset        = (page - 1) * limit
        paginated     = orders[offset: offset + limit]
        total_pages   = (total_transaksi + limit - 1) // limit if total_transaksi else 1

        return Response({
            "rekapitulasi": {
                "total_jumlah_transaksi": total_transaksi,
                "total_customer_unik":    customer_unik,
                "total_pendapatan":       total_pendapatan,
            },
            "pagination": {
                "page":        page,
                "limit":       limit,
                "total_pages": total_pages,
                "total_items": total_transaksi,
            },
            "data": paginated,
        }, status=status.HTTP_200_OK)
