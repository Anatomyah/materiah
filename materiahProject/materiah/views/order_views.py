from django.core.cache import cache
from django.db import transaction
from rest_framework import viewsets, filters, status
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Order
from ..permissions import DenySupplierProfile
from ..serializers.order_serializer import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id', 'quote__id', 'orderitem__quote_item__product__manufacturer__name']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [DenySupplierProfile()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        cache_key = f"orders_list"

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
        cache_keys = cache.get('orders_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('orders_list_keys', cache_keys)

        return response

    def get_queryset(self):
        return Order.objects.all().order_by('id')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        related_quote = instance.quote
        order_items = instance.orderitem_set.all()

        with transaction.atomic():
            if related_quote:
                related_quote.status = "RECEIVED"
                related_quote.save()

            if order_items:
                for item in order_items:
                    product = item.quote_item.product
                    product.stock -= item.quantity
                    product.save()

            instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
