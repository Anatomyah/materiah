from django.core.cache import cache
from rest_framework import status, filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Supplier, SupplierSecondaryEmails
from .permissions import DenySupplierProfile
from ..serializers.supplier_serializer import SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    """

    SupplierViewSet

    A viewset for managing suppliers.

    Attributes:
        queryset (QuerySet): A queryset of all suppliers.
        serializer_class (SerializerClass): The serializer class to use for serializing and deserializing supplier objects.
        pagination_class (PaginationClass): The pagination class to use for paginating the list of suppliers.
        filter_backends (List[FilterBackend]): A list of filter backends to use for filtering the list of suppliers.
        search_fields (List[str]): A list of fields to search for suppliers.

    Methods:
        get_permissions(): Returns a list of permissions to apply based on the current action.
        list(request, \*args, \**kwargs): Retrieves a list of suppliers.
        get_queryset(): Returns a queryset of suppliers with related objects prefetched.
        partial_update(request, \*args, \**kwargs): Partially updates a supplier.
        serve_supplier_select_list(request): Retrieves a list of suppliers for use in a select dropdown.
        check_email(request): Checks if an email already exists for a supplier.
        check_phone(request): Checks if a phone number already exists for a supplier.
        check_name(request): Checks if a name already exists for a supplier.
    """
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'manufacturersupplier__manufacturer__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
        Determines the permissions required for a given action and user.

        :return: A list of permission classes required for the action and user.
        """
        # Check if the current action is 'serve_supplier_select_list'
        if self.action == 'serve_supplier_select_list':
            # If so, return an instance of AllowAny permission class
            # This means any authenticated or unauthenticated user can access this view
            return [AllowAny()]
            # Otherwise, for other actions, check if the user is authenticated
        elif self.request.user.is_authenticated:
            # If the user is authenticated, return a list containing one instance of DenySupplierProfile
            # DenySupplierProfile is a custom permission class which should be defined elsewhere in your code
            return [DenySupplierProfile()]
            # If the user is not authenticated, return an empty list of permissions
        return []

    def list(self, request, *args, **kwargs):
        """
        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: The Django REST Framework response.

        This method is used to handle the HTTP GET request for listing suppliers. It takes the request object and any
        additional arguments specified as parameters. The method first checks if * the requested data is available in
        the cache using the cache key generated from the request parameters. If the data is found in the cache,
        it is returned as a response. Otherwise, * the method calls the parent class's list method to retrieve the
        data and paginates the queryset.

        If the paginated queryset is not found or its length is less than the page size specified in the pagination
        class, the 'next' field in the response data is set to None. The response * data is then cached with a
        timeout of 500 seconds and the cache key is added to the list of cache keys. Finally, the response is returned.

        Example usage:
        response = self.list(request, arg1, arg2, kwarg1=value1, kwarg2=value2)
        """
        # define some useful parameters from the request's query parameters
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]

        # create a key to be used for retrieving and storing information in the cache
        cache_key = f"supplier_list"
        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        # try to get data from cache
        cached_data = cache.get(cache_key)

        # if data exists in cache, you can return it directly
        if cached_data:
            return Response(cached_data)

        # if the cache doesn't contain any data, fetch it with the parent class' list method
        response = super().list(request, *args, **kwargs)

        # after you fetched data, you can decide if it needs to be paginated or not
        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

        # now you can store your data in cache for faster access next time
        cache_timeout = 500
        cache.set(cache_key, response.data, cache_timeout)

        # save the cache key for potential future reference
        cache_keys = cache.get('supplier_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('supplier_list_keys', cache_keys)

        # return the response containing the required data
        return response

    def get_queryset(self):
        """
        The method uses the Django's ORM to form a QuerySet that consists of all Suppliers. It uses the
        'prefetch_related()' method which is a Django QuerySet optimization to pre-fetch related objects for each
        Supplier in a single SQL query. This technique can drastically reduce the number of database queries
        performed and hence increases the performance of the view.

        The 'prefetch_related('manufacturersupplier_set__manufacturer', 'product_set')' fetches related Manufacturers
        and Products for each Supplier instance. These are then ordered by the Supplier name.

        :return: a queryset of suppliers ordered by their names and with pre-fetched related Manufacturers and Products.
        """
        return Supplier.objects.prefetch_related('manufacturersupplier_set__manufacturer',
                                                 'product_set').all().order_by('name')

    def partial_update(self, request, *args, **kwargs):
        """
        Partially updates a supplier instance.

        :param request: The HTTP request.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: The HTTP response.

        """
        # Extract the supplier id from the keyword arguments
        supplier_id = kwargs.get('pk')

        # Fetch the supplier instance that matches the given id
        instance = Supplier.objects.get(id=supplier_id)

        # Get the instance of our serializer, passing in the instance we fetched and the data from our request
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        # If the serializer's input is valid
        if serializer.is_valid():
            # Performing the update operation by calling the serializer's save method
            self.perform_update(serializer)
            # Return a successful HTTP response with a status code of 200 (OK)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If the serializer's input is not valid
        else:
            # Return an error HTTP response with a status code of 400 (BAD REQUEST)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def serve_supplier_select_list(self, request):
        """
        :param request: HttpRequest object that represents the incoming request. :return: Response object containing
        the suppliers list and a message if successful. If an exception occurs, an error message is returned with a
        status code of 500.

        This method serves the select options for the supplier list. It retrieves the list of suppliers from the
        database, orders them by name, formats them into a list of dictionaries with 'value' and 'label' keys,
        and returns a Response object with the formatted suppliers list and a success message.
        """
        try:
            # Query the database for all suppliers, returning only their id and name,
            # and order the results by the supplier name
            suppliers = Supplier.objects.values('id', 'name').order_by('name')

            # Transform the query result into a list of dictionaries,
            # each one representing a supplier with 'value' and 'label' keys
            ordered_formatted_suppliers = [{'value': s['id'], 'label': s['name']} for s in suppliers]

            # Return a success HTTP response with a status code of 200 (OK)
            # The response's content includes the list of formatted suppliers and a success message as JSON
            return Response(
                {"suppliers_list": ordered_formatted_suppliers, "message": 'Suppliers list fetched successfully'})

        except Exception as e:  # Catch any exceptions that might occur
            # In case of an error, return an error HTTP response with a status code of 500 (Internal Server Error)
            # The response's content includes the error message as JSON
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_email(self, request):
        """
        Check Email

        Checks if a given email is unique in the database.

        :param request: the HTTP request object
        :return: a response object with a JSON payload indicating the uniqueness status of the email
        """
        try:
            # Extract the email value from the query parameters in the incoming request
            entered_email = request.query_params.get('value', None)

            # Check if an instance of Supplier with that email exists in the database,
            # using a case-insensitive exact match query
            exists = Supplier.objects.filter(email__iexact=entered_email).exists()

            # If such instance does exist
            if exists:
                # Return a successful HTTP response with a JSON payload indicating that the email is not unique,
                # along with a message
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            # If no such instance exists
            else:
                # Return a successful HTTP response with a JSON payload indicating that the email is unique,
                # along with a message
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)

        except Exception as e:  # Catch any exceptions that might occur
            # In case of an error, return an error HTTP response with a status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_phone(self, request):
        """
        Check if a phone number exists in the Supplier model.

        :param request: The request object containing query parameters 'prefix' and 'suffix'.
        :type request: rest_framework.request.Request
        :return: Response with a JSON object indicating whether the phone number is unique and a corresponding message.
        :rtype: rest_framework.response.Response
        """
        try:
            # Extract the name from the query parameters of the request.
            entered_name = request.query_params.get('name', None)

            # Check if an instance of Supplier with the provided name (case-insensitive) already exists in the database.
            exists = Supplier.objects.filter(name__iexact=entered_name).exists()

            # If such a Supplier already exists...
            if exists:
                # ...return a successful response indicating that the name is not unique and a message stating the same.
                return Response({"unique": False, "message": "Name already exists"},
                                status=status.HTTP_200_OK)

            # If there is no such Supplier...
            else:
                # ...return a successful response indicating that the name is unique and a message stating the same.
                return Response({"unique": True, "message": "Name is available"}, status=status.HTTP_200_OK)

        except Exception as e:  # If an error occurs...
            # ...return a response with a status of 'Internal Server Error' and the error message.
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_name(self, request):
        """
        Check if a given name exists in the Supplier table.

        :param request: The request object.
        :return: A Response object with a JSON body indicating whether the name is unique or not.
        :rtype: Response
        """
        try:
            # Extract the name value from the 'name' query parameter in the incoming request
            entered_name = request.query_params.get('name', None)

            # Check if a supplier instance with the extracted name already exists or not in the DB
            exists = Supplier.objects.filter(name__iexact=entered_name).exists()

            # If such instance does exist
            if exists:
                # Return an HTTP response with a JSON payload indicating that the name is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Name already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the name is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Name is available"}, status=status.HTTP_200_OK)

        except Exception as e:  # If there's an error during the execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_secondary_email(self, request):
        """
        Check Email

        Checks if a given secondary supplier email is unique in the database.

        :param request: the HTTP request object
        :return: a response object with a JSON payload indicating the uniqueness status of the email
        """
        try:
            # Extract the email value from the query parameters in the incoming request
            entered_email = request.query_params.get('value', None)

            # Check if an instance of Supplier with that email exists in the database,
            # using a case-insensitive exact match query
            exists = SupplierSecondaryEmails.objects.filter(email__iexact=entered_email).exists()

            # If such instance does exist
            if exists:
                # Return a successful HTTP response with a JSON payload indicating that the email is not unique,
                # along with a message
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            # If no such instance exists
            else:
                # Return a successful HTTP response with a JSON payload indicating that the email is unique,
                # along with a message
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)

        except Exception as e:  # Catch any exceptions that might occur
            # In case of an error, return an error HTTP response with a status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
