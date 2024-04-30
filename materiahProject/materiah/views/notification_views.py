from django.core.cache import cache
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .paginator import MateriahPagination
from .permissions import DenySupplierProfile
from ..models import OrderNotifications, ExpiryNotifications
from ..serializers.notifications_serializer import OrderNotificationSerializer, ExpiryNotificationSerializer


class OrderNotificationViewSet(viewsets.ModelViewSet):
    """
    OrderNotificationViewSet class

    A viewset for managing order notifications.

    Attributes:
    - `queryset`: A queryset that retrieves all OrderNotifications objects.
    - `serializer_class`: The serializer class to use for serializing and deserializing OrderNotifications objects.
    - `pagination_class`: The pagination class to use for paginating the list of order notifications.
    - `filter_backends`: A list of filter backends to use for filtering the list of order notifications.
    - `search_fields`: A list of fields to search for when performing a search on the list of order notifications.

    Methods:
    - `get_permissions()`: Get the list of permissions that the viewset requires for the current action.
    - `list(request, *args, **kwargs)`: List all order notifications with optional pagination and search.
    - `get_queryset()`: Get the queryset for retrieving order notifications.

    """
    queryset = OrderNotifications.objects.all()
    serializer_class = OrderNotificationSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
        Returns the list of permissions based on the provided parameters.

        :return: A list of permissions.
        """
        if self.action == 'names':
            # Allow any authenticated user
            return [AllowAny()]

        elif self.request.user.is_authenticated:
            # Apply DenySupplierProfile for other actions where the user is authenticated.
            # This could be extending the logic to any action that needs specific user authorization.
            return [DenySupplierProfile()]

            # For unauthenticated requests or those not falling into the above categories, no permissions are applied.
        return []

    def list(self, request, *args, **kwargs):
        """
        :param request: The HTTP request object.
        :param args: Positional arguments.
        :param kwargs: Keyword arguments.
        :return: The HTTP response object.

        This method is used to return a list of order notifications. It takes in a request object from the Django framework, along with any additional positional or keyword arguments. The method
        * first checks if the requested data is already cached, and if so, returns the cached data. If not, it calls the superclass's list method to retrieve the data and performs additional
        * operations.

        The method constructs a cache key based on the provided parameters in the request and attempts to fetch data from the cache using the key. If the data is not available in the cache,
        * it calls the superclass's list method to get the response.

        Next, the method checks if the retrieved data represents a full page of results or not. If the page is not full, it sets the 'next' key in the response data to None.

        The method then sets a cache timeout duration and caches the current response data using the generated cache key. It also updates the list of cache keys by appending the new key.

        Finally, the method returns the response object.
        """
        # An array of tuples indicating the parameters to check in the request
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None)),
            ('supplier_id', request.query_params.get('supplier_id', '')),
        ]
        # Base cache key
        cache_key = "order_notifications_list"

        # Constructs a more specific cache key if certain parameters are defined
        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        # Attempts to fetch data from the cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)  # Returns cached data if available

        # Calls the superclass's list method if cached data is not available
        response = super().list(request, *args, **kwargs)

        # Ensures that a 'next' key exists in response.data
        # And if the page isn't full, it sets 'next' to None
        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

            # Sets the cache timeout duration
        cache_timeout = 500
        # Caches the current response
        cache.set(cache_key, response.data, cache_timeout)

        # Retrieves current list of cache keys
        # And appends the new key
        cache_keys = cache.get('order_notifications_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('order_notifications_list_keys', cache_keys)

        return response

    def get_queryset(self):
        """
        Get the queryset for the specified parameters.

        :return: The filtered queryset based on the specified parameters.
        """
        # Fetch the base queryset from the parent method
        queryset = super().get_queryset()

        # Fetch the supplier ID provided in the parameters
        supplier_id_param = self.request.query_params.get('supplier_id', None)

        # If a specific supplier's ID is provided, only fetch their products
        if supplier_id_param:
            queryset = queryset.filter(product__supplier__id=supplier_id_param)

        return queryset.order_by('id')


class ExpiryNotificationViewSet(viewsets.ModelViewSet):
    """
    ExpiryNotificationViewSet

    viewsets.ModelViewSet subclass for handling ExpiryNotifications.

    Attributes:
        queryset (QuerySet): The queryset representing the ExpiryNotifications instances.
        serializer_class (Serializer): The serializer class for the ExpiryNotifications instances.
        pagination_class (Pagination): The pagination class for the list view.
        filter_backends (list): The list of filter backends for applying search filters.
        search_fields (list): The list of fields to be used for search filtering.

    Methods:
        get_permissions: Returns the permission classes based on the current action.
        list: Retrieves a list of ExpiryNotifications instances from cache or database and returns the response.
        get_queryset: Returns the queryset based on the request parameters.

    """
    queryset = ExpiryNotifications.objects.all()
    serializer_class = ExpiryNotificationSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
        Returns a list of permissions based on the given criteria.

        :return: A list of permissions.
        """
        if self.action == 'names':
            # Allow any authenticated user
            return [AllowAny()]

        elif self.request.user.is_authenticated:
            # Apply DenySupplierProfile for other actions where the user is authenticated.
            # This could be extending the logic to any action that needs specific user authorization.
            return [DenySupplierProfile()]

            # For unauthenticated requests or those not falling into the above categories, no permissions are applied.
        return []

    def list(self, request, *args, **kwargs):
        """
        :param request: The HTTP request object.
        :param args: Positional arguments.
        :param kwargs: Keyword arguments.
        :return: The HTTP response object.

        This method is used to return a list of expiry notifications. It takes in a request object from the Django
        framework, along with any additional positional or keyword arguments. The method * first checks if the
        requested data is already cached, and if so, returns the cached data. If not, it calls the superclass's list
        method to retrieve the data and performs additional * operations.

        The method constructs a cache key based on the provided parameters in the request and attempts to fetch data
        from the cache using the key. If the data is not available in the cache, * it calls the superclass's list
        method to get the response.

        Next, the method checks if the retrieved data represents a full page of results or not. If the page is not
        full, it sets the 'next' key in the response data to None.

        The method then sets a cache timeout duration and caches the current response data using the generated cache
        key. It also updates the list of cache keys by appending the new key.

        Finally, the method returns the response object.
        """
        # An array of tuples indicating the parameters to check in the request
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None)),
            ('supplier_id', request.query_params.get('supplier_id', '')),
        ]
        # Base cache key
        cache_key = "expiry_notifications_list"

        # Constructs a more specific cache key if certain parameters are defined
        for param, value in params:
            if value:
                cache_key += f"_{param}_{value}"

        # Attempts to fetch data from the cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)  # Returns cached data if available

        # Calls the superclass's list method if cached data is not available
        response = super().list(request, *args, **kwargs)

        # Ensures that a 'next' key exists in response.data
        # And if the page isn't full, it sets 'next' to None
        paginated_queryset = self.paginate_queryset(self.get_queryset())
        if paginated_queryset is None or len(paginated_queryset) < self.pagination_class.page_size:
            response.data['next'] = None

            # Sets the cache timeout duration
        cache_timeout = 500
        # Caches the current response
        cache.set(cache_key, response.data, cache_timeout)

        # Retrieves current list of cache keys
        # And appends the new key
        cache_keys = cache.get('expiry_notifications_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('expiry_notifications_list_keys', cache_keys)

        return response

    def get_queryset(self):
        """
        Fetches the base queryset from the parent method and then filters it based on the provided parameters.

        :return: The filtered queryset.
        """
        # Fetch the base queryset from the parent method
        queryset = super().get_queryset()

        # Fetch the supplier ID provided in the parameters
        supplier_id_param = self.request.query_params.get('supplier_id', None)

        # If a specific supplier's ID is provided, only fetch their products
        if supplier_id_param:
            queryset = queryset.filter(product_item__product__supplier__id=supplier_id_param)

        return queryset.order_by('id')
