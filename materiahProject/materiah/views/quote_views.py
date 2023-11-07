from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Quote
from .permissions import DenySupplierProfile
from ..serializers.quote_serializer import QuoteSerializer
from ..serializers.s3 import delete_s3_object


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return_data = serializer.data

        if 'presigned_url' in serializer.context:
            return_data['presigned_url'] = serializer.context['presigned_url']

        return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        headers = self.get_success_headers(serializer.data)
        return_data = serializer.data

        if 'presigned_url' in serializer.context:
            return_data['presigned_url'] = serializer.context['presigned_url']

        return Response(return_data, status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            if delete_s3_object(object_key=instance.s3_quote_key):
                instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

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

    @action(detail=False, methods=['POST'])
    def update_quote_upload_status(self, request):
        upload_status = request.data
        error = None

        try:
            quote = Quote.objects.get(id=upload_status['quote_id'])
            quote_upload_status = quote.fileuploadstatus

            if upload_status['status'] == 'completed':
                quote.status = 'RECEIVED'
                quote.save()
                quote_upload_status.delete()
            else:
                quote.delete()

        except ObjectDoesNotExist as e:
            error = e
        except Exception as e:
            error = e
        #         todo - add error logging

        if error:
            return Response(
                {
                    "error": "Unable to upload quote file due to a server error. Please try again."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({"message": "Image upload statuses updated successfully"}, status=status.HTTP_200_OK)
