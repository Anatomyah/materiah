from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Order, OrderImage
from .permissions import DenySupplierProfile
from ..serializers.order_serializer import OrderSerializer
from ..s3 import delete_s3_object


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id', 'quote__id', 'orderitem__quote_item__product__name',
                     'orderitem__quote_item__product__cat_num', 'quote__supplier_name']

    def get_permissions(self):
        if self.request.user.is_authenticated:
            return [DenySupplierProfile()]
        return []

    def list(self, request, *args, **kwargs):
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        cache_key = f"order_list"

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

        cache_timeout = 1
        cache.set(cache_key, response.data, cache_timeout)
        cache_keys = cache.get('order_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('order_list_keys', cache_keys)

        return response

    def get_queryset(self):
        return Order.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return_data = serializer.data

        if 'presigned_urls' in serializer.context:
            return_data['presigned_urls'] = serializer.context['presigned_urls']

        return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        headers = self.get_success_headers(serializer.data)
        return_data = serializer.data

        if 'presigned_urls' in serializer.context:
            return_data['presigned_urls'] = serializer.context['presigned_urls']

        return Response(return_data, status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        related_quote = instance.quote
        order_items = instance.orderitem_set.all()
        print(instance)
        print(order_items)

        try:
            with transaction.atomic():
                if related_quote:
                    related_quote.status = "RECEIVED"
                    related_quote.save()

                order_images = instance.orderimage_set.all()
                if order_images:
                    for image in order_images:
                        if delete_s3_object(object_key=image.s3_image_key):
                            image.delete()

                if order_items:
                    for item in order_items:
                        product = item.quote_item.product
                        product.stock -= item.quantity
                        product.save()

                instance.delete()

        except Exception as e:
            raise ValidationError(f"Error occurred: {str(e)}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['POST'])
    def update_image_upload_status(self, request):
        upload_statuses = request.data
        image_errors = []

        for image_id, upload_status in upload_statuses.items():
            try:
                order_image = OrderImage.objects.get(id=image_id)
                image_upload_status = order_image.fileuploadstatus

                if upload_status == "failed":
                    order_image.delete()
                else:
                    image_upload_status.delete()

            except ObjectDoesNotExist:
                image_errors.append(image_id)
            except Exception as e:
                image_errors.append(str(e))

        if image_errors:
            return Response(
                {
                    "errors": image_errors
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({"message": "Image upload statuses updated successfully"}, status=status.HTTP_200_OK)
