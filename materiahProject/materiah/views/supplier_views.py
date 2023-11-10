from django.core.cache import cache
from rest_framework import status, filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Supplier
from .permissions import DenySupplierProfile
from ..serializers.supplier_serializer import SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'manufacturersupplier__manufacturer__name']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [DenySupplierProfile()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        cache_key = f"supplier_list"

        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        cache_timeout = 10
        cache.set(cache_key, response.data, cache_timeout)
        cache_keys = cache.get('supplier_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('supplier_list_keys', cache_keys)

        return response

    def get_queryset(self):
        return Supplier.objects.prefetch_related('manufacturersupplier_set__manufacturer',
                                                 'product_set').all().order_by('name')

    def partial_update(self, request, *args, **kwargs):
        supplier_id = kwargs.get('pk')

        instance = Supplier.objects.get(id=supplier_id)

        serializer = self.get_serializer(instance, data=request.data,
                                         partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def serve_supplier_select_list(self, request):
        suppliers = Supplier.objects.values('id', 'name').order_by('name')
        ordered_formatted_suppliers = [{'value': s['id'], 'label': s['name']} for s in suppliers]
        return Response(ordered_formatted_suppliers)

    @action(detail=False, methods=['GET'])
    def check_email(self, request):
        try:
            entered_email = request.query_params.get('value', None)
            print(entered_email)
            exists = Supplier.objects.filter(email=entered_email).exists()
            if exists:
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
