from django.core.cache import cache
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Quote
from ..permissions import DenySupplierProfile
from ..serializers.quote_serializer import QuoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id', 'order__id', 'supplier__name', 'quoteitem__product__manufacturer__name']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [DenySupplierProfile()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        cache_key = f"quotes_list"

        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        print(response.data['results'])

        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        cache_timeout = 10
        cache.set(cache_key, response.data, cache_timeout)
        cache_keys = cache.get('quote_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('quote_list_keys', cache_keys)

        return response

    def get_queryset(self):
        return Quote.objects.all().order_by('id')

    @action(detail=False, methods=['GET'])
    def serve_open_quotes_select_list(self, request):
        try:
            open_quotes = Quote.objects.filter(order__isnull=True, status='RECEIVED').values('id', 'creation_date',
                                                                                             'supplier__name').order_by(
                'id')
            ordered_formatted_open_quotes = [
                {'value': q['id'], 'label': f"{q['id']} - {q['creation_date']} - {q['supplier__name']}"}
                for q in open_quotes]
            return Response(ordered_formatted_open_quotes)
        except Exception as e:
            return Response({"error": "Unable to fetch quotes. Please try again later"}, status=500)
