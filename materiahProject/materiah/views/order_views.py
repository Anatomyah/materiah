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
    """
    Class representing the viewset for managing orders.

    Attributes:
        queryset: A queryset representing all the orders.
        serializer_class: The serializer class for the orders.
        pagination_class: The pagination class for paginating the orders.
        filter_backends: The filter backends used for filtering the orders.
        search_fields: The fields used for searching the orders.

    Methods:
        get_permissions: Returns the permissions for the current user.
        list: Retrieves a list of orders.
        get_queryset: Retrieves the queryset for the orders.
        create: Creates a new order.
        update: Updates an existing order.
        destroy: Deletes an order.
        update_image_upload_status: Updates the upload status of images.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id', 'quote__id', 'orderitem__quote_item__product__name',
                     'orderitem__quote_item__product__cat_num', 'quote__supplier_name']

    def get_permissions(self):
        """
        Returns the permissions for the current user.

        :return: A list of permissions for the current user. If the user is authenticated, it returns a
                 list containing the permission 'DenySupplierProfile'. If the user is not authenticated,
                 it returns an empty list.
        """
        if self.request.user.is_authenticated:
            # If user is authenticated, use DenySupplierProfile permission
            return [DenySupplierProfile()]
        else:
            # When the user is not authenticated, return an empty list of permissions
            # Resulting in permission denied.
            return []

    def list(self, request, *args, **kwargs):
        """
        Method: list

        Description: This method is used to retrieve a list of objects. It is an overridden method from the parent class.

        :param request: The request object containing the query parameters.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A Response object containing the list of objects.

        Example Usage:
        ```python
        response = list(request, *args, **kwargs)
        ```
        """
        # Define parameters to be expected in the request
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        # Initialize cache key
        cache_key = f"order_list"

        # Modify cache key with parameters if they are provided in the request
        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        # Try to get cached data
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # If cache exists, return cached data as response
            return Response(cached_data)

        # If cache doesn't exist, perform default list operation and get response
        response = super().list(request, *args, **kwargs)

        # Get paginated queryset
        paginated_queryset = self.paginate_queryset(self.get_queryset())
        # Check if paginated queryset isn't full, and modify `next` value to None
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        # Set cache timeout duration
        cache_timeout = 500
        # Add response to cache
        cache.set(cache_key, response.data, cache_timeout)

        # Append current cache key to list of cache keys for order list
        cache_keys = cache.get('order_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('order_list_keys', cache_keys)

        # Return response
        return response

    def get_queryset(self):
        """
        Returns the queryset of all orders, ordered by id.

        :return: QuerySet of Order objects
        """
        return Order.objects.all().order_by('id')

    def create(self, request, *args, **kwargs):
        """
        :param request: The HTTP request object.
        :param args: Additional positional arguments passed to the method.
        :param kwargs: Additional keyword arguments passed to the method.
        :return: A Response object containing the serialized data and necessary headers.

        This method is used to create a new object based on the provided request data. It first obtains the data serializer using the `get_serializer` method and validates the serializer's data
        *. If the data is valid, it saves the object and gets the success headers using the `get_success_headers` method.

        The serialized data is then returned in a Response object with the HTTP status code 201 (Created) and the necessary headers. If the serializer context contains presigned URLs, they are
        * also added to the returned data.
        """
        # Get the serializer with the request data
        serializer = self.get_serializer(data=request.data)
        # Validate the data
        serializer.is_valid(raise_exception=True)
        # Save the validated data as an order instance
        order = serializer.save()

        # Generate headers for the success response
        headers = self.get_success_headers(serializer.data)
        # Prepare data for the response
        return_data = serializer.data

        # If presigned URLs are provided in the request, include them in the response
        if 'presigned_urls' in serializer.context:
            return_data['presigned_urls'] = serializer.context['presigned_urls']

        # Return a success response with the created order data
        return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Update method

        :param request: The HTTP request object
        :param args: additional arguments passed to the method
        :param kwargs: additional keyword arguments passed to the method
        :return: Response with updated data

        This method updates an instance with the given data in the HTTP request, using the serializer. It performs validation on the serialized data and then calls the perform_update method
        *. After updating the instance, it retrieves the success headers and returns the updated data in a response. If there are presigned URLs in the serializer's context, it adds them to
        * the returned data.
        """
        # Fetch the Order instance based on the provided id in the URL
        instance = self.get_object()

        # Pass the existing instance and the new data from the request to the serializer for validation
        serializer = self.get_serializer(instance, data=request.data)
        # Check if the new data is valid. If not, raise an exception.
        serializer.is_valid(raise_exception=True)

        # If the data is valid, perform the update operation.
        self.perform_update(serializer)

        # Create headers for the successful response
        headers = self.get_success_headers(serializer.data)
        # Prepare the updated data for the response
        return_data = serializer.data

        # If there are presigned_urls included in the request, add them to the response data
        if 'presigned_urls' in serializer.context:
            return_data['presigned_urls'] = serializer.context['presigned_urls']

        # Send a success response back with the updated data
        return Response(return_data, status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        """
        Overrides the destroy method from the base class (viewsets.ModelViewSet).

        This method deletes an Order instance and performs multiple related operations within
        an atomic transaction block. These operations include: updating the status of related
        quotes, modifying the product stock based on order items, and deleting related
        order images.

        If any operation fails, it raises a ValidationError with a message of what happened.

        On successful deletion, it returns an HTTP 204 No Content response.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A response indicating success or failure.

        """
        # Get the object that needs to be deleted
        instance = self.get_object()

        # Get related quote and order items of the instance
        related_quote = instance.quote
        order_items = instance.orderitem_set.all()

        try:
            # Wrap all database operations inside an atomic transaction block
            with transaction.atomic():
                # If there is a related quote, update its status
                if related_quote:
                    related_quote.status = "RECEIVED"
                    related_quote.save()

                # Get all images related to the order
                order_images = instance.orderimage_set.all()

                # If there are images, delete each one of them after removing them from S3 storage
                if order_images:
                    for image in order_images:
                        if delete_s3_object(object_key=image.s3_image_key):
                            image.delete()

                # If there are order items, update the corresponding product stock
                if order_items:
                    for item in order_items:
                        product = item.quote_item.product
                        product.stock -= item.quantity
                        product.save()
                # operations have been performed, delete the instance
                instance.delete()

        except Exception as e:
            # If any error occurs during the transaction, raise a validation error with the exception message
            raise ValidationError(f"Error occurred: {str(e)}")
        # Return an HTTP 204 No Content response if the deletion is successful
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['POST'])
    def update_image_upload_status(self, request):
        """
        An action that updates the upload status of an image in the Order instance.
        'detail=False' means this action doesn't work on a single record.

        The function iterates through the provided data in the POST request, updating
        upload statuses of images accordingly. It deletes an image or its upload status
        based on the particular status value.

        If the image id provided doesn't correspond to any OrderImage instance, the id is
        collected in an error list. Any other exceptions raised during the process are
        also included in this error list.

        On successful execution, a message indicating success is returned along with
        HTTP 200 OK status.

        If any errors occurred during the process, a list of all errors is returned with
        HTTP 404 Not Found status.

        :param request: The HTTP request object.
        :return: The HTTP response object.

        """
        # Extract the upload statuses of images from the request data
        upload_statuses = request.data
        # Initialize list to collect ids of non-existent images or exceptions
        image_errors = []

        # Iterate over upload statuses dictionary
        for image_id, upload_status in upload_statuses.items():
            try:
                # Get the corresponding order image and its upload status
                order_image = OrderImage.objects.get(id=image_id)
                image_upload_status = order_image.fileuploadstatus

                # If the upload status is 'failed', delete this image
                if upload_status == "failed":
                    order_image.delete()
                # Otherwise, delete the image upload status
                else:
                    image_upload_status.delete()

            # Catch the case where the image does not exist, add the id to the error list
            except ObjectDoesNotExist:
                image_errors.append(image_id)

            # Catch any other exceptions, add the exception message to the error list
            except Exception as e:
                image_errors.append(str(e))

        # If any errors occurred, return a response containing the errors and a 404 status
        if image_errors:
            return Response(
                {
                    "errors": image_errors
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # If no errors occurred, return a successful response
        return Response({"message": "Image upload statuses updated successfully"}, status=status.HTTP_200_OK)
