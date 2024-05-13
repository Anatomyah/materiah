from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .paginator import MateriahPagination
from ..models import Product, ProductImage, ProductItem
from .permissions import ProfileTypePermission
from ..serializers.product_serializer import ProductSerializer, ProductItemSerializer
from ..s3 import delete_s3_object


class ProductViewSet(viewsets.ModelViewSet):
    """
    :class:`ProductViewSet` defines the viewset for handling CRUD operations for the `Product` model.

    Attributes: - queryset (QuerySet): Specifies the queryset for retrieving all product objects. - serializer_class
    (Serializer): Specifies the serializer class for serializing and deserializing `Product` objects. -
    pagination_class (Pagination): Specifies the pagination class for paginating the list of products. -
    filter_backends (List[Filter]): Specifies the list of filter backends to apply for filtering products. -
    search_fields (List[str]): Specifies the list of fields to search products by.

    Methods: - get_permissions: Returns the list of permissions required for the current user. - list: Retrieves a
    list of products with optional filtering, pagination, and caching. - get_queryset: Retrieves the queryset for
    retrieving products with optional filtering by supplier and catalog status. - retrieve: Retrieves a specific
    product by its ID. - create: Creates a new product. - update: Updates an existing product. - destroy: Deletes an
    existing product. - names: Retrieves a list of product names for autocomplete suggestions. -
    update_image_upload_status: Updates the status of product image uploads. - check_cat_num: Checks if a catalog
    number is unique. - update_stock_item: Updates the stock quantity of a product.

    Note: This class inherits from `viewsets.ModelViewSet`, which provides the default behavior for handling CRUD
    operations on a model.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'cat_num', 'supplier__name', 'manufacturer__name']

    def get_permissions(self):
        """
        Retrieves the permissions for the current user.

        :return: A list of permissions. If the user is authenticated, it contains a single `ProfileTypePermission`
        object. Otherwise, an empty list is returned.
        """
        # Check if the user is authenticated
        if self.request.user.is_authenticated:
            # If the user is authenticated, use ProfileTypePermission
            return [ProfileTypePermission()]
        else:
            # When the user is not authenticated, return an empty list of permissions
            # This implies that non-authenticated users are not granted any permissions
            return []

    def list(self, request, *args, **kwargs):
        """
        Overrides the list method from viewsets.ModelViewSet to provide custom implementation
        for fetching a list of Product instances. The method begins by setting up parameters
        associated with the request.

        It leverages Django's caching system to fetch results from the cache if they are available.
        If the cache is not available, it calls the parent class's list method to fetch the data,
        apply pagination if required and generates a response.

        If the generated paginated queryset isn't at full capacity,
        it modifies the 'next' value of the result to None (i.e., disables the 'next' page button).

        The resultant data is then cached, and its key stored in a list for future references.
        Finally, it returns the response.

        :param request: The HTTP request object.
        :param args: Positional arguments.
        :param kwargs: Keyword arguments.
        :return: The response object.
        """
        # Define parameters to be expected in the request
        params = [
            ('page_num', request.query_params.get('page_num', None)),
            ('search', request.query_params.get('search', '')),
            ('supplier_id', request.query_params.get('supplier_id', '')),
        ]

        # Additional parameters to distinguish between supplier and regular view
        if request.is_supplier:
            params.append(('supplier_id', request.user.supplieruserprofile.supplier.id))
            params.append(('view_type', 'supplier_view'))
        else:
            params.append(('view_type', 'regular_view'))

        # Parameter for supplier catalogue
        if request.query_params.get('supplier_catalogue', '') == 'true':
            params.append(('supplier_shop_catalogue', 'True'))

        # Initialize cache key
        cache_key = f"product_list"

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
        # Append current cache key to list of cache keys for product list
        cache_keys = cache.get('product_list_keys', [])
        cache_keys.append(cache_key)
        cache.set('product_list_keys', cache_keys)

        # Return response
        return response

    def get_queryset(self):
        """
        Overrides the get_queryset method from django-rest-framework's ModelViewSet.

        This method returns a QuerySet that will be used as the result for the
        view. Depending on the parameters provided in the request, it tailors
        the QuerySet to contain Products from a specified supplier or Products
        that are set to display on the supplier's catalogue.

        If the method is called during a list operation, it filters the products
        based on their 'supplier_cat_item' attribute. This attribute, when true,
        signifies that the product is displayed on the supplier's catalogue.
        The exact behaviour (showing or hiding such items) can be controlled
        by the 'supplier_catalogue' parameter in the request.

        The returned QuerySet sorts the products by their 'name'.

        :param self: the current instance of the class
        :return: a queryset object containing the filtered results
        """
        # Fetch the base queryset from the parent method
        queryset = super().get_queryset()

        # Fetch any supplier ID provided in the parameters
        supplier_id_param = self.request.query_params.get('supplier_id', None)
        # Fetch supplier_catalogue parameter (if any)
        supplier_catalogue = self.request.query_params.get('supplier_catalogue', None)

        # If the requester is a supplier, only fetch their own products marked as supplier catalogue items
        if self.request.is_supplier:
            supplier_profile_id = self.request.user.supplieruserprofile.supplier.id
            queryset = queryset.filter(supplier=supplier_profile_id, supplier_cat_item=True)

        # If a specific supplier's ID is provided, only fetch their products
        if supplier_id_param:
            queryset = queryset.filter(supplier_id=supplier_id_param)
        # If it's a list operation, filter the products based on their 'supplier_cat_item' attribute according
        # to 'supplier_catalogue' parameter
        if self.action == 'list':
            if supplier_catalogue:
                # If 'supplier_catalogue' is true, only show products that are on the supplier's catalogue
                queryset = queryset.filter(supplier_cat_item=True)
            else:
                # If 'supplier_catalogue' is not true, hide the products that are on the supplier's catalogue
                queryset = queryset.filter(supplier_cat_item=False)

        # Return a sorted list of products based on the name
        return queryset.order_by('name')

    def create(self, request, *args, **kwargs):
        """
        Overrides the create method from the super class `viewsets.ModelViewSet`.

        This method begins by getting a serializer with the incoming request data for product creation.
        It verifies that the provided data is valid, and if it is, it creates a new Product instance from this data.

        It also checks for the presence of 'presigned_urls' (i.e., pre-signed S3 URLs for image files) in the
        serializer's context. If any are found, they are added to the response data along with the serialized product
        details.

        :param request: The HTTP request containing the data to create the resource.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: The created resource data.
        """
        # Instantiate the serializer with the request data
        serializer = self.get_serializer(data=request.data)

        # Validate the request data
        serializer.is_valid(raise_exception=True)

        # If the validation is successful, save the validated data as a Product instance
        product = serializer.save()

        # Generate headers for the success response
        headers = self.get_success_headers(serializer.data)
        # Prepare data for the response
        return_data = serializer.data

        # If presigned URLs are provided in the request, include them in the response
        if 'presigned_urls' in serializer.context:
            return_data['presigned_urls'] = serializer.context['presigned_urls']

        # Return an HTTP 201 Created response with the new Product data
        return Response(return_data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Overrides the update method from the viewsets.ModelViewSet.

        This method begins by getting the Product instance that needs to be updated.
        It then passes the existing instance and the new data from the request to the
        serializer for validation. If the new data is valid, then the update operation
        is performed. The updated data is prepared for the response.

        The method also checks for any 'presigned_urls' in the serializer's context,
        and if present, includes them in the response.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional arguments passed to the method.
        :type args: tuple
        :param kwargs: Additional keyword arguments passed to the method.
        :type kwargs: dict

        :return: The updated object data.
        :rtype: Response

        """

        # Fetch the Product instance that needs to be updated
        instance = self.get_object()

        # Pass the existing instance and the new data from the request to the serializer for validation
        serializer = self.get_serializer(instance, data=request.data)

        # Validate the data
        serializer.is_valid(raise_exception=True)

        # If the data is valid, perform the update operation
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
        Overrides the destroy method from the base ModelViewSet.

        It starts by fetching the `Product` instance to delete using the `get_object()`
        method from its superclass. It then performs the deletion of the product instance.

        Prior to deleting the `Product` itself, the method deletes all associated `ProductImage`
        instances. It checks their S3 storage keys and uses the method `delete_s3_object` to delete
        the files from the S3 storage. If the S3 object is successfully deleted, the corresponding
        `ProductImage` in the database is deleted.

        All the deletion operations are enclosed in a transaction block to ensure consistency in the
        operations. If any of them fails, the other operations are rolled back.

        :param request: The HTTP request.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments (not used).
        :return: Returns a response with a status code indicating success or failure.
        :rtype: rest_framework.response.Response
        """
        # Get the Product object that needs to be deleted
        instance = self.get_object()

        # Wrap all database operations inside an atomic transaction block
        with transaction.atomic():
            # Get all images related to this product
            product_images = instance.productimage_set.all()
            # If there are any images, delete each one of them after removing them from S3 storage
            if product_images:
                for image in product_images:
                    if delete_s3_object(object_key=image.s3_image_key):
                        image.delete()

            # After all related operations have been performed, delete the Product instance
            instance.delete()

        # Return an HTTP 204 No Content response if the deletion is successful
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'])
    def names(self, request):
        """
         A custom action to return a list of Product objects in a simplified format.

        This method is not specific to any Product instance (detail=False), so it doesn't operate on a single record.

        With or without the supplier's ID as a query parameter, the function queries the database for products and
        generates a list of products represented as dictionaries. Each product contains its 'id', 'cat_num'(catalogue
        number), and 'name' and is ordered by 'name'.

        If the 'supplier_id' query parameter is present, only Products from that supplier are returned.

        :param request: The request object.
        :type request: Request
        :return: A list of formatted products.
        :rtype: Response

        If any exceptions are raised during the process, an HTTP error response is returned with the
        exception's message and corresponding status code.
        """
        try:
            # Check if a supplier's id is provided
            supplier_id = request.query_params.get('supplier_id', None)
            # If a supplier's id is provided, get products for that supplier, excluding supplier catalogue items
            if supplier_id:
                products = (Product.objects.filter(supplier_id=supplier_id, supplier_cat_item=False)
                            .values('id', 'cat_num', 'name').order_by('name'))
            else:
                # If a supplier's id is not provided, get all products, excluding supplier catalogue items
                products = (Product.objects.filter(supplier_cat_item=False).values('id', 'cat_num', 'name')
                            .order_by('name'))

            # Format the products to have 'value' and 'label' keys and return them
            ordered_formatted_products = [{'value': p['id'], 'label': f"{p['cat_num']} ({p['name']})"} for p in
                                          products]

            # Return the formatted list of products
            return Response(ordered_formatted_products)

            # If the requested objects do not exist, return a 404 Not Found response
        except ObjectDoesNotExist:
            return Response({"error": "Supplier not found"}, status=404)

            # If any other exception occurs, catch it and return a 500 Internal Server Error response
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['POST'])
    def update_image_upload_status(self, request):
        """
        This is a custom action in the `ProductViewSet` not particular to a specific Product instance.
        Its purpose is to handle updates on image upload statuses of various ProductImage instances.

        The function iterates through the provided data in the POST request, getting the image id and its respective
        upload status. Depending on the upload status, it either deletes the image or its 'upload_status' status.

        The method compiles a list of ids for which the operation failed due to either the image being non-existent or
        due to an exception during execution.

        If no errors occur during the process, a message indicating a successful operation is returned. If any errors
        occur, a list of all errors is returned.

        :param request: The request object containing the upload statuses.
        :return: A response object indicating the result of the update.
        """
        # Extract the upload statuses of images from the request data
        upload_statuses = request.data

        # Initialize list to collect ids of non-existent images or exceptions
        image_errors = []

        # Iterate over upload statuses dictionary
        for image_id, upload_status in upload_statuses.items():
            try:
                # Get the corresponding product image and its upload status
                product_image = ProductImage.objects.get(id=image_id)
                image_upload_status = product_image.fileuploadstatus

                # If the upload status is 'failed', delete this image
                if upload_status == "failed":
                    product_image.delete()
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

    @action(detail=False, methods=['GET'])
    def check_cat_num(self, request):
        """
        Check if a catalog number exists in the Product database.

        :param request: An HTTP request object. :return: A Response object with a JSON payload indicating if the
        catalog number is unique and a corresponding message.
        """
        try:
            # Get the catalogue number from the request parameters
            entered_cat_num = request.query_params.get('value', None)

            # Check if the catalogue number exists in the system for non-supplier catalog items
            exists = Product.objects.filter(cat_num__iexact=entered_cat_num, supplier_cat_item=False).exists()

            # If the catalogue number exists, return a Response indicating that it's not unique
            if exists:
                return Response(
                    {"unique": False, "message": "Catalog number already exists"},
                    status=status.HTTP_200_OK
                )
            else:
                # If the catalogue number does not exist, return a Response indicating that it's unique
                return Response(
                    {"unique": True, "message": "Catalog number is available"},
                    status=status.HTTP_200_OK
                )

            # If an exception occurs, catch it and return a 500 Internal Server Error Response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def update_product_stock(self, request):
        """
        Updates the stock of a product.

        :param request: The request object containing the product_id
                        and value to update the stock.
        :return: Returns a response with a message if the stock is updated
                 successfully, or an error if there was an exception.

        :rtype: Response
        """
        try:
            # access 'product_id' from the request data
            product_id = request.data.get('product_id')

            # access 'value' (the amount to change the product stock) from the request data
            value = request.data.get('value')

            # get the Product object using the 'product_id'
            product = Product.objects.get(id=product_id)

            # update the product stock
            product.stock = value

            # save changes made to the product's stock
            product.save()

            # return a successful response along with HTTP 200 status code once the product stock is updated
            return Response({"message": f"Updated product {product_id} stock successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            # catch any exceptions, convert the exception to a string, and send an HTTP 500 status code along with
            # the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['POST'])
    def create_stock_item(self, request):
        """
        Create a stock item for a product.

        :param request: The HTTP request object.
        :return: The HTTP response with the created stock item information or an error.
        """

        data = request.data.copy()

        # Convert date strings to date objects
        if not data['expiry']:
            data['expiry'] = None
        if not data['opened_on']:
            data['opened_on'] = None

        try:
            # create an instance of the stock item and relating it to the relevant product using that data
            stock_item = ProductItem.objects.create(**data)

            # create a serializer instance with the newly created stock_item instance
            serializer = ProductItemSerializer(stock_item)
            # return a successful response along with the stock_item representation and an HTTP 200 status code once the
            # stock item is successfully created
            return Response({"message": f"Stock item {stock_item.id} created successfully",
                             'stock_item': serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            # catch any exceptions, convert the exception to a string, and send an HTTP 500 status code along with
            # the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['PATCH'])
    def update_stock_item(self, request):
        """
        Update the stock item.

        :param request: The request object containing the data for updating the stock item.
        :type request: Request
        :return: The response with the updated stock item data.
        :rtype: Response
        """

        # store the necessary data into variables to create the stock item
        item_id = request.data.get('item_id')
        batch = request.data.get('batch')
        in_use = request.data.get('in_use', False)
        expiry = request.data.get('expiry')
        opened_on = request.data.get('opened')

        try:
            # fetch the ProductItem instance matching the item_id and update it's fields with the updated data
            stock_item = ProductItem.objects.get(id=item_id)
            stock_item.batch = batch
            stock_item.in_use = in_use
            stock_item.expiry = expiry
            stock_item.opened_on = opened_on
            stock_item.save()

            # return a successful response along with HTTP 200 status code once the ProductItem is updated
            return Response({"message": f"Stock item {stock_item.id} updated successfully"},
                            status=status.HTTP_200_OK)

        except Exception as e:
            # catch any exceptions, convert the exception to a string, and send an HTTP 500 status code along with
            # the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['DELETE'])
    def delete_stock_item(self, request):
        """
        Deletes a stock item from the product inventory.

        :param request: The HTTP request object containing the item ID to be deleted.
        :return: Returns a response object with a success message if the deletion is successful, or an error message if any exception occurs.

        """

        # store the item ID into a variable
        item_id = request.GET.get('item_id')

        try:
            # fetch and delete that item
            stock_item = ProductItem.objects.get(id=item_id)
            stock_item.delete()

            # return a successful response along with HTTP 200 status code once the ProductItem is deleted
            return Response({"message": f"Stock item {stock_item.id} deleted successfully"},
                            status=status.HTTP_200_OK)

        except Exception as e:
            # catch any exceptions, convert the exception to a string, and send an HTTP 500 status code along with
            # the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['PATCH'])
    def update_product_item_stock(self, request):
        """
        This method updates the stock of a product item.

        :param request: The HTTP request object containing the data to update the stock.
            - item_id: The ID of the product item to update.
            - updated_stock: The new stock value to update the item with.

        :return: A HTTP response object with a success or error message along with an appropriate status code.
            - If the stock item is successfully updated, the response will have a message "Stock item <item_id> updated successfully"
              with a status code of 200 (OK).
            - If an exception occurs during the update process, the response will have an error message describing the exception,
              along with a status code of 500 (Internal Server Error).
        """
        # store the necessary data into variables to create the stock item
        item_id = request.data.get('item_id')
        updated_stock = request.data.get('updated_stock')
        try:
            # fetch the ProductItem instance matching the item_id and update it's stock
            stock_item = ProductItem.objects.get(id=item_id)
            stock_item.item_stock = updated_stock
            stock_item.save()

            # return a successful response along with HTTP 200 status code once the ProductItem is updated
            return Response({"message": f"Stock item {stock_item.id} updated successfully"},
                            status=status.HTTP_200_OK)

        except Exception as e:
            # catch any exceptions, convert the exception to a string, and send an HTTP 500 status code along with
            # the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
