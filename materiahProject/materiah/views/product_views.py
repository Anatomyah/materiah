from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Product
from ..permissions import ProfileTypePermission
from ..serializers.product_serializer import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'cat_num']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [ProfileTypePermission()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', '')),
            ('supplier_id', request.query_params.get('supplier_id', '')),
        ]

        if request.is_supplier:
            params.append(('supplier_id', request.user.supplieruserprofile.supplier.id))
            params.append(('view_type', 'supplier_view'))
        else:
            params.append(('view_type', 'regular_view'))

        if request.query_params.get('supplier_catalogue', '') == 'true':
            params.append(('supplier_shop_catalogue', 'True'))

        cache_key = f"product_list"

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
        cache_keys = cache.get('product_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('product_list_keys', cache_keys)

        return response

    def get_queryset(self):
        queryset = super().get_queryset()
        supplier_id_param = self.request.query_params.get('supplier_id', None)
        supplier_catalogue = self.request.query_params.get('supplier_catalogue', None)

        if self.request.is_supplier:
            supplier_profile_id = self.request.user.supplieruserprofile.supplier.id
            queryset = queryset.filter(supplier=supplier_profile_id, supplier_cat_item=True)
        if supplier_id_param:
            queryset = queryset.filter(supplier_id=supplier_id_param)
        if supplier_catalogue:
            queryset = queryset.filter(supplier_cat_item=True)

        return queryset.order_by('name')

    @action(detail=False, methods=['GET'])
    def names(self, request):
        try:
            supplier_id = request.query_params.get('supplier_id', None)
            products = Product.objects.filter(supplier_id=supplier_id).values('id', 'cat_num', 'name').order_by(
                'name')
            ordered_formatted_products = [{'value': p['id'], 'label': f"{p['cat_num']} ({p['name']})"} for p in
                                          products]
            return Response(ordered_formatted_products)
        except ObjectDoesNotExist:
            return Response({"error": "Supplier not found in our database"}, status=404)
        except Exception as e:
            return Response({"error": "Unable to fetch manufacturers. Please try again"}, status=500)
