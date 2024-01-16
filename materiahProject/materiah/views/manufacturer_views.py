from django.core.cache import cache
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Manufacturer
from .permissions import DenySupplierProfile
from ..serializers.manufacturer_serializer import ManufacturerSerializer


class ManufacturerViewSet(viewsets.ModelViewSet):
    """
    ManufacturerViewSet

    A ViewSet for handling manufacturer-related actions.

    Attributes:
        queryset (QuerySet): A queryset of all manufacturers.
        serializer_class (Serializer): The serializer class for manufacturers.
        pagination_class (Pagination): The pagination class for paginating the queryset.
        filter_backends (list): A list of filter backends to use for filtering manufacturers.
        search_fields (list): A list of fields to search for manufacturers.

    Methods:
        get_permissions: Gets the permissions for the view based on the action.
        list: Retrieves a list of manufacturers, optionally paginated and cached.
        get_queryset: Retrieves the queryset of all manufacturers, ordered by name.
        names: Retrieves a list of manufacturer names.
        check_name: Checks if a manufacturer name is unique.

    """
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
           Overrides the method from the base class (viewsets.ModelViewSet) to implement custom permissions logic.
           This is invoked every time a request is made to the API.
           It returns a list of permission classes that should be applied to the action handler.
           This method distinguishes between an action handler that retrieves names ('names') and other authenticated actions.
           It assumes that non-authenticated actions supply an empty list of permissions.
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
            Overrides the list method from the base class (viewsets.ModelViewSet).

            This method retrieves a list of all Manufacturers, and also handles requests with page_num
            and search parameters. It uses Django's caching framework to avoid excess database
            queries for the same requests.

            The response data is cached and will be returned for subsequent identical requests
            until the cache timeout expires.
            """
        # An array of tuples indicating the parameters to check in the request
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', None))
        ]
        # Base cache key
        cache_key = "manufacturer_list"

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
        cache_keys = cache.get('manufacturer_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('manufacturer_list_keys', cache_keys)

        return response

    def get_queryset(self):
        """
        Get the queryset of manufacturers with related suppliers and products, ordered by name.

        :return: A queryset of Manufacturer objects with prefetch_related suppliers and product_set, ordered by name.
        :rtype: QuerySet
        """
        queryset = Manufacturer.objects.prefetch_related('suppliers', 'product_set').all().order_by('name')
        return queryset

    @action(detail=False, methods=['GET'])
    def get_manufacturer_select_list(self, request):
        """
        Fetches a QuerySet of dictionaries for each manufacturer, each containing 'id' and 'name' fields.

        :param request: HTTP request object
        :return: HTTP response object containing a successful response with a list of formatted manufacturers and a confirmation message
        :rtype: Response

        :raises: Exception if any error occurs during the process

        """
        # Store the supplier ID for filtering if sent
        supplier_id = request.GET.get('supplier_id', None)

        try:
            # Fetches a QuerySet of dictionaries for each manufacturer, each containing 'id' and 'name' fields,
            # filtering by supplier if a supplier ID was provided
            if supplier_id:
                manufacturers = (Manufacturer.objects.filter(suppliers__id=supplier_id).values('id', 'name')
                                 .order_by('name'))
            else:
                manufacturers = (Manufacturer.objects.values('id', 'name').order_by('name'))

            # Formats the manufacturers in a list, where each item is a dictionary
            # with 'value' set to the 'id' and 'label' set to the 'name'
            ordered_formatted_manufacturers = [{'value': m['id'], 'label': m['name']} for m in manufacturers]

            # Returns a successful response containing the manufacturers list and a confirmation message
            return Response(
                {'manufacturer_list': ordered_formatted_manufacturers,
                 "message": "Manufacturer List fetched successfully"})

        except Exception as e:
            # Captures any raised exceptions and returns an error message in the response, along with a 500 status code
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_name(self, request):
        """
        Check Name

        Checks if a name exists in the Manufacturer model.

        :param request: The HTTP request object.
        :return: A JSON response indicating if the name is unique or not.

        """
        try:
            # Fetches the 'name' query parameter from the request
            entered_name = request.query_params.get('name', None)

            # Performs a case-insensitive search in the Manufacturer model for the entered_name
            exists = Manufacturer.objects.filter(name__iexact=entered_name).exists()

            # If the entered name exists, return a successful response indicating:
            # the name isn't unique and an appropriate message
            if exists:
                return Response({"unique": False, "message": "Name already exists"},
                                status=status.HTTP_200_OK)
            # If the entered name doesn't exist, return a successful response indicating:
            # the name is unique and an appropriate message
            else:
                return Response({"unique": True, "message": "Name is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            # Captures any raised exceptions and returns an error message in the response,
            # along with a 500 internal server error status code
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
