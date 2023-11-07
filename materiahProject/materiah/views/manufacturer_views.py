from django.core.cache import cache
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Manufacturer
from .permissions import DenySupplierProfile
from ..serializers.manufacturer_serializer import ManufacturerSerializer


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [DenySupplierProfile()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        cache_key = "manufacturers_list"

        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        cache_timeout = 10
        cache.set(cache_key, response.data, cache_timeout)
        cache_keys = cache.get('manufacturers_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('manufacturers_list_keys', cache_keys)

        return response

    def get_queryset(self):
        queryset = Manufacturer.objects.prefetch_related('suppliers', 'product_set').all().order_by('name')
        return queryset

    @action(detail=False, methods=['GET'])
    def names(self, request):
        try:
            manufacturers = Manufacturer.objects.values('id', 'name').order_by('name')
            ordered_formatted_manufacturers = [{'value': m['id'], 'label': m['name']} for m in manufacturers]
            return Response(ordered_formatted_manufacturers)
        except Exception as e:
            return Response({"error": "Unable to fetch manufacturers. Please try again later"}, status=500)
