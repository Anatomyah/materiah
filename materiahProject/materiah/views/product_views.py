from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Product, ProductImage
from .permissions import ProfileTypePermission
from ..serializers.product_serializer import ProductSerializer
from ..s3 import delete_s3_object


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'cat_num', 'supplier__name', 'manufacturer__name']

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

        cache_timeout = 500
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

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

        with transaction.atomic():
            product_images = instance.productimage_set.all()
            if product_images:
                for image in product_images:
                    if delete_s3_object(object_key=image.s3_image_key):
                        image.delete()

            instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

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
            return Response({"error": "Supplier not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['POST'])
    def update_image_upload_status(self, request):
        upload_statuses = request.data
        image_errors = []

        for image_id, upload_status in upload_statuses.items():
            try:
                product_image = ProductImage.objects.get(id=image_id)
                image_upload_status = product_image.fileuploadstatus

                if upload_status == "failed":
                    product_image.delete()
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

    @action(detail=False, methods=['GET'])
    def check_cat_num(self, request):

        try:
            entered_cat_num = request.query_params.get('value', None)
            exists = Product.objects.filter(cat_num__iexact=entered_cat_num, supplier_cat_item=False).exists()

            if exists:
                return Response({"unique": False, "message": "Catalog number already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Catalog number is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
