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
    RiwayatPembayaranSerializer
)
from accounts.models import User
from catalogs.models import Ternak, Daging, Invest
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Q
from rest_framework.views import APIView
from django.contrib.contenttypes.models import ContentType
import decimal
from rest_framework.pagination import PageNumberPagination

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
        """
        queryset = super().get_queryset()
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

        # PBI-23: Jika customer tidak ditemukan → return 404 Not Found
        try:
            customer = User.objects.get(id=id_customer)
            if customer.role != 'Customer':
                return Response({"detail": "User yang dipilih bukan merupakan customer."}, status=status.HTTP_400_BAD_REQUEST)
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
                        return Response({"detail": f"Ternak {tid} tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

                # Create Pesanan
                pesanan = Pesanan.objects.create(
                    customer=customer,
                    catatan=catatan,
                    status_pesanan='Diproses',
                    updated_at=timezone.now()
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
        PBI-28: Update Status Pesanan Mazdafarm (Strict Validation)
        """
        instance = self.get_object_or_404_by_id(kwargs.get('pk'))
        
        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)
        
        # 2. Status validity
        if new_status not in ['Diproses', 'Selesai', 'Dibatalkan']:
             return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Payment Validation for Selesai
        if new_status == 'Selesai':
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
                if new_status == 'Selesai':
                    # Fill payment data (though strictly should be 0 remainder already)
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    for item in items:
                        item.ternak.status_ternak = 'Terjual'
                        item.ternak.save()
                elif new_status == 'Dibatalkan':
                    for item in items:
                        item.ternak.status_ternak = 'Tersedia'
                        item.ternak.save()
                    
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
        """
        queryset = super().get_queryset()
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

        try:
            customer = User.objects.get(id=id_customer)
            if customer.role != 'Customer':
                return Response({"detail": "User yang dipilih bukan merupakan customer."}, status=status.HTTP_400_BAD_REQUEST)
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
        
        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response({"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Diproses', 'Selesai', 'Dibatalkan']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Payment Validation for Selesai
        if new_status == 'Selesai':
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
                if new_status == 'Selesai':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    # Stock logic for Daging (if any specific status needed)
                    for item in items:
                        item.daging.status_daging = 'Terjual'
                        item.daging.save()
                elif new_status == 'Dibatalkan':
                    for item in items:
                        item.daging.status_daging = 'Tersedia'
                        item.daging.save()

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
            'items__invest'
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
                    updated_at=timezone.now(),
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
        """
        PBI-28: Update Status Pesanan Invest Ternak
        """
        instance = self._get_pesanan_or_404(kwargs.get('pk'))

        # 1. Block transition FROM Selesai/Dibatalkan
        if instance.status_pesanan in ['Selesai', 'Dibatalkan']:
            return Response(
                {"detail": "Pesanan yang sudah selesai atau dibatalkan tidak dapat diupdate kembali."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = request.data.get('status_pesanan', instance.status_pesanan)
        catatan = request.data.get('catatan', instance.catatan)

        if new_status not in ['Diproses', 'Selesai', 'Dibatalkan']:
            return Response({"detail": "Status pesanan tidak valid."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Payment Validation for Selesai
        if new_status == 'Selesai':
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
                if new_status == 'Selesai':
                    pembayaran = instance.pembayaran
                    pembayaran.sudah_dibayar += (pembayaran.tagihan + pembayaran.menunggu_persetujuan)
                    pembayaran.tagihan = 0
                    pembayaran.menunggu_persetujuan = 0
                    pembayaran.save()
                    
                    for item in items:
                        item.invest.status_investernak = 'Closed'
                        item.invest.save()
                elif new_status == 'Dibatalkan':
                    for item in items:
                        item.invest.status_investernak = 'Open'
                        item.invest.save()

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
        if order.status_pesanan == 'Dibatalkan':
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
                    status='Menunggu Verifikasi',
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

        if riwayat.status != 'Menunggu Verifikasi':
            return Response({"detail": "Pembayaran ini sudah diverifikasi."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Validate decisions
        keputusan = request.data.get('keputusan')
        if keputusan not in ['Diterima', 'Ditolak']:
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
                if keputusan == 'Diterima':
                    pembayaran.sudah_dibayar += riwayat.nominal_pembayaran
                    pembayaran.menunggu_persetujuan -= riwayat.nominal_pembayaran
                    riwayat.status = 'Diterima'
                    
                    # Logic: If tagihan is 0, this order is effectively fully paid (ready to be Selesai)
                    ready_to_complete = (pembayaran.tagihan == 0 and pembayaran.menunggu_persetujuan == 0)
                else:
                    pembayaran.tagihan += riwayat.nominal_pembayaran
                    pembayaran.menunggu_persetujuan -= riwayat.nominal_pembayaran
                    riwayat.status = 'Ditolak'
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
    queryset = RiwayatPembayaran.objects.all()
    serializer_class = RiwayatPembayaranSerializer
    permission_classes = [IsFinance]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        if status_filter:
            return self.queryset.filter(status=status_filter)
        return self.queryset