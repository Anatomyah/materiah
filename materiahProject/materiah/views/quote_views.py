from django.core.cache import cache
from django.db import transaction
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Quote
from .permissions import DenySupplierProfile
from ..serializers.quote_serializer import QuoteSerializer
from ..s3 import delete_s3_object


class QuoteViewSet(viewsets.ModelViewSet):
    """
    The QuoteViewSet class is a subclass of viewsets.ModelViewSet in Django REST Framework. It provides CRUD (Create, Retrieve, Update, Delete) functionalities for the Quote model.

    Attributes:
    - `queryset`: A QuerySet of all Quote instances. It is used to retrieve and manipulate the data.
    - `serializer_class`: The serializer class used to convert the Quote instances to JSON format and vice versa.
    - `pagination_class`: The pagination class used to paginate the list view of quotes.
    - `filter_backends`: A list of filter backends used to filter the quotes based on certain criteria.
    - `search_fields`: A list of fields used for searching quotes.

    Methods:
    - `get_permissions()`: Returns the list of permissions required to access the QuoteViewSet. If the user is authenticated, it returns a list containing the DenySupplierProfile permission
    *. Otherwise, it returns an empty list.
    - `list(request, *args, **kwargs)`: Retrieves a paginated list of quotes. It first checks if the requested data is available in the cache. If not, it calls the list method of the parent
    * class to retrieve the data and then caches the response. It also updates the cache keys.
    - `get_queryset()`: Returns the QuerySet of all Quote instances ordered by their IDs.
    - `create(request, *args, **kwargs)`: Creates a new Quote instance. It validates the data using the serializer, saves the instance, and returns a response with the created quote data
    *.
    - `update(request, *args, **kwargs)`: Updates an existing Quote instance. It retrieves the instance, validates the data using the serializer, performs the update, and returns a response
    * with the updated quote data.
    - `destroy(request, *args, **kwargs)`: Deletes an existing Quote instance. It retrieves the instance, deletes the associated object in S3, and returns a response with no content.
    - `serve_open_quotes_select_list(request)`: Retrieves a list of open quotes that are not associated with any order. It formats the list of quotes and returns a response containing the
    * formatted data.
    - `update_quote_upload_status(request)`: Updates the upload status of a quote. It retrieves the quote, updates its status, and returns a response with a success message.

    Note: The examples are not included in the documentation as requested.
    """
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['id', 'order__id', 'supplier__name', 'quoteitem__product__manufacturer__name',
                     'quoteitem__product__cat_num', 'quoteitem__product__name']

    def get_permissions(self):
        """
        Get the permissions for the current user.

        :return: A list of permission instances for the user.
        """
        # 'is_authenticated' is a flag that indicates if the user is authenticated.
        if self.request.user.is_authenticated:
            # If the user is authenticated, return a list containing one instance of DenySupplierProfile
            # DenySupplierProfile is a custom permission class which should be defined elsewhere in your code
            return [DenySupplierProfile()]
            # If the user is not authenticated, return an empty list of permissions
        return []

    def list(self, request, *args, **kwargs):
        """
        Overrides the `list` method from the `viewsets.ModelViewSet`.

        This method fetches a list of Quote instances.

        In addition to basic listing functionality, this method caches results under different cache keys based on
        the pagination and search parameters provided. Thus, for subsequent requests with the same parameters,
        the cached data is returned, reducing database query overhead and improving response time.

        :param request: The HTTP request object.
        :param args: Any additional positional arguments.
        :param kwargs: Any additional keyword arguments.
        :return: The HTTP response.
        """
        # Prepare cache key using base key ('quote_list') and additional parameters based on request query parameters
        params = [
            ('page_num', request.query_params.get('page_num', None)),  # Get page number from request
            ('search', request.query_params.get('search', None)),  # Get search phrase from request
            ('fulfilled_filter', request.query_params.get('fulfilled_filter', False))  # Get fulfilled filter param from
            # request
        ]

        cache_key = f"quote_list"
        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"  # Create unique cache key for each parameter-value pair

        # Check if we have this data in cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # Return data from cache if available
            return Response(cached_data)

        # If data is not in cache, fetch it
        response = super().list(request, *args, **kwargs)

        # Apply Pagination
        paginated_queryset = self.paginate_queryset(self.get_queryset())
        # If there are no items on the next page, make 'next' as None in the response data
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        # Set cache timeout of 500 seconds
        cache_timeout = 500

        # Add the fetched data to the cache using the composed cache key
        cache.set(cache_key, response.data, cache_timeout)

        # Also, add the cache key to a master list in the cache for tracking all cache keys used in this view
        # This is particularly useful for managing, invalidating, or refreshing cache records as part of larger system behavior
        cache_keys = cache.get('quote_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('quote_list_keys', cache_keys)

        # Return the fetched data after the caching mechanism
        return response

    def get_queryset(self):
        """
            Returns the queryset of all Quote objects, applying filters based on the action.
            For list actions, it applies the 'fulfilled_filter'. For retrieve actions, it returns all quotes.
            """
        queryset = Quote.objects.all().order_by('creation_date')

        # Apply filters only for list actions
        if self.action == 'list':
            fulfilled_filter = self.request.query_params.get('fulfilled_filter', None)

            if fulfilled_filter:
                queryset = queryset.filter(status='FULFILLED')
            else:
                queryset = queryset.exclude(status='FULFILLED')

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Overrides the 'create' method from `viewsets.ModelViewSet` to add custom behavior.

        This method handles POST requests to create a new Quote instance.

        Data for the new quote is passed in the POST request. The JSON data is passed to the serializer,
        which validates the data. If the data is valid, the quote is saved and a response containing the saved quote
        data is returned.

        The method also checks for any 'presigned_url' in the serializer's context, and if present, includes it in the response.

        :param request: The request object containing the data to create a new resource.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Returns a Response object with the serialized data of the created resource.

        """
        # Use the serializer to validate the data passed in the request
        serializer = self.get_serializer(data=request.data)

        # Call is_valid(raise_exception=True) to automatically return a 400 Response if data not valid
        serializer.is_valid(raise_exception=True)

        # If the data is valid, save the data passed and create a new quote object
        quote = serializer.save()

        # Prepare headers for the successful response
        headers = self.get_success_headers(serializer.data)

        # Prepare the created quote data for the response
        return_data = serializer.data

        # If there's a presigned_url included in the request, add it to the response data
        if 'presigned_url' in serializer.context:
            return_data['presigned_url'] = serializer.context['presigned_url']
        # Return the newly created quote data along with HTTP 201 CREATED status
        return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Overrides the 'update' method from `viewsets.ModelViewSet` to add custom behavior.

        This method handles PUT requests to update an existing Quote instance.

        The method receives data in the request to update the quote, fetches the existing quote using
        Django's in-built method 'get_object' and updates the instance with the new data.

        The method also checks for a 'presigned_url' key in the serializer context and appends it
        to the returned data when appropriate.

        :param request: The request object that contains the updated data.
        :param args: Additional positional arguments (not used in this method).
        :param kwargs: Additional keyword arguments (not used in this method).

        :return: A Response object with the updated data and appropriate status.
        """
        # Fetch the quote instance that is to be updated
        instance = self.get_object()

        # Use the serializer to validate the updated data passed in the request
        serializer = self.get_serializer(instance, data=request.data)

        # If the updated data is valid, save it and update the quote object
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Prepare headers for the response
        headers = self.get_success_headers(serializer.data)

        # Prepare the updated quote data for returning in the response
        return_data = serializer.data

        # If there's a 'presigned_url' in the serializer context, append it to the response data
        if 'presigned_url' in serializer.context:
            return_data['presigned_url'] = serializer.context['presigned_url']

        # Return the updated quote data along with an HTTP 200 OK status
        return Response(return_data, status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        """
        Overrides the 'destroy' method from `viewsets.ModelViewSet` to add custom behavior.

        This method handles DELETE requests to remove an existing Quote instance.

        Before deleting the quote object, it makes sure to delete the associated file hosted on S3 using an object key.

        The whole operation is performed inside a transaction block to ensure that the filesystem state and
        database state remain consistent.

        :param request: The request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :return: Response with status 204 if the object is successfully deleted.
        """
        # Get the quote object to be deleted
        instance = self.get_object()

        # Use a transaction block to ensure filesystem (S3) and database state consistency
        with transaction.atomic():
            # Attempt to delete the file related to the quote from S3 using the object key
            # Function `delete_s3_object()` should be defined to handle deletion in your S3 bucket
            if delete_s3_object(object_key=instance.s3_quote_key):
                # If the file is successfully deleted from S3, delete the quote object from the database
                instance.delete()

        # Returns an HTTP 204 NO CONTENT status indicating successful deletion
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'])
    def serve_open_quotes_select_list(self, request):
        """
        Custom method which adds additional capability to the `QuoteViewSet`.

        This method handles GET requests to fetch a list of open quotes. The list contains the id, creation date and
        supplier name of each quote. The list is then formatted into a list of dictionary items where `value` is the quote id
        and `label` is a string combining id, creation date and supplier name.

        :param request: The incoming HTTP request.
        :return: The HTTP response with open quotes select list.
        """
        try:
            # Fetch 'RECEIVED' status quotes excluding those associated with an order and order the result by id
            open_quotes = Quote.objects.filter(
                order__isnull=True, status='RECEIVED'
            ).values('id', 'creation_date', 'supplier__name').order_by('id')

            # Format the fetched quotes into a list of dictionary items with 'value' key for quote id
            # and 'label' key combining id, creation date and supplier name
            ordered_formatted_open_quotes = [
                {'value': q['id'], 'label': f"{q['id']} - {q['creation_date']} - {q['supplier__name']}"}
                for q in open_quotes]

            # Return the prepared list of quotes along with HTTP 200 OK status
            return Response(
                {"quotes": ordered_formatted_open_quotes, "message": "Image upload statuses updated successfully"},
                status=status.HTTP_200_OK)

        except Exception as e:
            # In case of any exception, return an HTTP 500 status and the error message
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['POST'])
    def update_quote_upload_status(self, request):
        """
        A custom action method to handle the status update of a quote file upload operation.

        This method handles POST requests. The request data carries the 'quote_id' (ID of the quote) and the 'status' of
        the file upload operation (either 'completed' or any other status).

        If the 'status' in the request data is 'completed', then the status of the quote is set to 'RECEIVED' and along with
        the deletion of the corresponding fileuploadstatus record. If 'status' is anything other than 'completed', then the
        quote itself is deleted.

        :param request: The HTTP request object.
            - `quote_id`: The ID of the quote to update the upload status for.
            - `status`: The new upload status. Valid values are 'completed'.
        :return: An HTTP response with a message indicating the result of the update.
            - HTTP 200 OK: The upload statuses were updated successfully.
                - `message`: A string indicating the success message.
            - HTTP 404 Not Found: An error occurred during the update.
                - `error`: A string describing the error that occurred.
        """
        # Get the upload status from the request data
        upload_status = request.data

        try:
            # From the upload status, get the id of the quote
            quote = Quote.objects.get(id=upload_status['quote_id'])

            # Get the fileuploadstatus corresponding to the quote
            quote_upload_status = quote.fileuploadstatus

            # If the upload status is marked as 'completed'
            if upload_status['status'] == 'completed':
                # Update quote status to 'RECEIVED'
                quote.status = 'RECEIVED'
                quote.save()

                # Then, delete the fileuploadstatus record
                quote_upload_status.delete()
            else:
                # If the upload status is NOT 'completed', delete the quote
                quote.delete()

            # Return success message and status
            return Response({"message": "Image upload statuses updated successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            # If an exception occurs, return error message and status
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
