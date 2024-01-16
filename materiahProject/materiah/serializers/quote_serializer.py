import json
from django.core.mail import send_mail
from django.db import transaction
from django.http import QueryDict
from django.template.loader import render_to_string
from rest_framework import serializers
from decimal import Decimal

from .product_serializer import ProductSerializer
from ..s3 import create_presigned_post, delete_s3_object
from ..models import Supplier, Product, Order
from ..models.file import FileUploadStatus
from ..models.quote import Quote, QuoteItem


class QuoteItemSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize/deserialize `QuoteItem` instances.

    Attributes:
        product (ProductSerializer): Read-only serializer for `Product` instances.

    Meta:
        model (QuoteItem): The `QuoteItem` model class to serialize/deserialize.
        fields (List[str]): The fields to include in the serialized output.

    """
    product = ProductSerializer(read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'quote', 'product', 'quantity', 'price']


class QuoteSerializer(serializers.ModelSerializer):
    """
           QuoteSerializer is a ModelSerializer class for serializing and deserializing 'Quote' instances.
           It provides serialization and deserialization methods for Quote instances and includes some custom methods
           and extended functionalities like fetching related objects data, creating multiple quotes, updating quote files,
           changing product and reverting prices, and handling S3 uploads.

           Attributes:
               items (SerializerMethodField): A field representing associated QuoteItems.
               supplier (SerializerMethodField): a field representing associated Supplier.
               status (SerializerMethodField): a field representing Quote's status.
               order (SerializerMethodField): a field representing associated Order.
           Meta:
               model (Quote): The 'Quote' model class to serialize/deserialize.
               fields (list[str]): The fields to include in the serialized output.

       """
    items = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = ['id', 'quote_url', 'supplier', 'request_date', 'creation_date', 'last_updated', 'items',
                  'status', 'order']

    @staticmethod
    def get_supplier(obj):
        """
        Get supplier information for a given object.

        :param obj: The object or a list of objects for which to retrieve supplier information.
        :return: A dictionary containing the supplier id and name if a single object is specified,
                 otherwise a list of dictionaries containing the supplier id and name for each object in the list.
        """
        if isinstance(obj, list):
            return [{'id': supplier.id, 'name': supplier.name} for supplier in Supplier.objects.filter(quote__in=obj)]
        else:
            supplier = Supplier.objects.filter(quote=obj).first()
            return {'id': supplier.id, 'name': supplier.name}

    @staticmethod
    def get_items(obj):
        """
        Retrieve quote items from the given object.

        :param obj: The object from which to retrieve quote items.
        :type obj: list or object

        :return: The serialized quote items.
        :rtype: list
        """
        # Check if the provided object is a list
        if isinstance(obj, list):
            # If it is, return a list of serialized data for all QuoteItems for each quote object in the list
            return [QuoteItemSerializer(quote.quoteitem_set.all(), many=True).data for quote in obj]
        else:
            # If it's not a list, i.e., it's a single object, return serialized data for the QuoteItems of the quote object
            return QuoteItemSerializer(obj.quoteitem_set.all(), many=True).data

    @staticmethod
    def get_status(obj):
        """
        :param obj: The object for which the status will be retrieved. It can be either a single object or a list of objects.
        :return: If `obj` is a list, a list of status values is returned, corresponding to each object in the list. If `obj` is a single object, the status value of that object is returned.

        .. note::
           The `get_status_display()` method is assumed to be available on the `obj` object. It is expected to return a human-readable representation of the status.

        """
        # Check if the provided object is a list
        if isinstance(obj, list):
            # If it is, return a list of status for each quote object in the list
            # get_status_display is a Django model method that returns the human-readable version of a field's value
            return [item.get_status_display() for item in obj]
        else:
            # If it's not a list, return the status of the single quote object
            return obj.get_status_display()

    @staticmethod
    def get_order(obj):
        """
        :param obj: The object or list of objects for which to retrieve the order.
        :return: The id of the order if it exists, or None if no order is found.
        """
        # Check if the provided object is a single quote
        if isinstance(obj, Quote):
            # If it is, get the order related to that quote
            order = Order.objects.filter(quote=obj).first()
            # If order exists, return its id, otherwise return None
            return order.id if order else None
        else:
            # If the object is a list of quotes, iterate through each quote
            order_ids = []
            for quote in obj:
                # Get the order related to the current quote
                order = Order.objects.filter(quote=quote).first()
                # If an order exists, append its id to the order_ids list
                if order:
                    order_ids.append(order.id)
            # Finally, return the list of retrieved order ids
            return order_ids

    def to_representation(self, instance):
        """
        Method to transform the serialized representation of an instance to remove the order key if
        the quote is not related to an order

        :param instance: The instance to be serialized.
        :return: The serialized representation of the instance.
        """
        representation = super(QuoteSerializer, self).to_representation(instance)
        if representation.get('order') is None:
            # If 'order' key exist and its value is None, remove 'order' from dictionary
            representation.pop('order')

        return representation

    @transaction.atomic
    def create(self, validated_data):
        """
           Overrides the default create method for handling the creation of Quote instances.

           This method is called when a new instance is created using the serializer's `save()` method.

           It obtains request data from serializer's context and checks if 'quote_file_type' is provided in the request.
           If request data is an instance of QueryDict, it is converted into a regular Python dictionary.

           If 'quote_file_type' is provided in the request data and the request is to manually create a quote,
           a single quote is created and a presigned URL is provided for uploading a file to the storage service.

           If multiple quotes are to be created, it calls create_multiple_quote method.

           If 'quote_file_type' is provided and multiple quotes are not to be created,
           it creates a single quote and the associated file is uploaded to the storage service.

           Args:
               validated_data (dict): Data that is already validated by serializer.

           Returns:
               dict or Quote: If a file is being uploaded, returns a dictionary containing the created quote and the presigned URL for file upload.
                              Otherwise, returns the created quote instance.

           Raises:
               Exception: If 'quote_file_type' cannot be obtained from the request data.

           """
        # Get the request data from the serializer's context
        request_data = self.context.get('request').data
        quote_file_type = None

        # Try to extract 'quote_file_type' from the request data
        try:
            quote_file_type = request_data['quote_file_type']
        except Exception as e:
            pass

        # Check if the request data is of type QueryDict
        if isinstance(request_data, QueryDict):

            # Convert QueryDict request data to Python dictionary
            request_data = self.convert_querydict_to_dict(request_data)

            # If quote_file_type is provided and request is for manual creation
            if quote_file_type:

                # Call the create_single_quote method providing the necessary data
                # and obtain the single quote and presigned URL
                quote_and_presigned_url = self.create_single_quote(
                    request_data=request_data,
                    quote_file_type=quote_file_type,
                    manual_creation=True)

                # Store the presigned URL in the context for later use
                self.context['presigned_url'] = quote_and_presigned_url['presigned_url']

                # Return the created quote
                return quote_and_presigned_url['quote']
            else:
                # If quote_file_type not provided, call create method for single quote
                return self.create_single_quote(request_data=request_data,
                                                manual_creation=True)

        # If more than one supplier quote is provided in the request data
        if len(request_data.keys()) > 1:
            # Call method to create multiple quotes
            return self.create_multiple_quote(request_data=request_data)
        else:
            # If only one supplier quote is provided and quote_file_type is present
            # call the create_single_quote method to create a single quote and upload the file
            # If quote_file_type is not present, a single quote is created
            return self.create_single_quote(request_data=request_data,
                                            quote_file_type=quote_file_type)

    @transaction.atomic
    def update(self, instance, validated_data):
        """
            Overrides the default update method for handling the modification of Quote instance.

            This method is responsible for updating the details of an existing Quote.
            It modifies the Quote items' price and quantity as per the request.
            In the case of a file being associated with a Quote, the method handles the deletion of the existing file from the storage
            and provides a presigned URL for the upload of the new file.

            Args:
                instance (Quote): The Quote object that is to be updated.
                validated_data (dict): A dictionary containing the new data for the update.

            Returns:
                dict or Quote: If a file update is requested in the data, a dictionary containing updated Quote instance and the presigned
                               URL for file upload is returned. Otherwise, the updated Quote instance is returned.

            Raises:
                serializers.ValidationError: If a Quote item does not exist for the provided id in the request data.
            """
        # Fetch the data for the items to be updated from the request
        items_data = json.loads(self.context['request'].data.get('items', '[]'))
        # Try to extract 'quote_file_type' from the request data
        quote_file_type = self.context.get('request').data.get('quote_file_type')

        # Iterate over all the items in items_data
        for item_data in items_data:
            # Convert the price and quantity values to appropriate types
            price_as_decimal = Decimal(item_data['price'])
            quantity_as_integer = int(item_data['quantity'])
            # Flag to track any changes made
            changes = False

            # Try to fetch the QuoteItem
            try:
                quote_item = QuoteItem.objects.get(id=item_data['quote_item_id'])
            except QuoteItem.DoesNotExist as e:
                # If a QuoteItem does not exist for the provided id, raise a validation error
                raise serializers.ValidationError(str(e))

            # If the product id for the current quote item differs from the product id in the request
            if quote_item.product_id != item_data['product']:
                # Check if quote_item price exists
                if not quote_item.price:
                    revert = False
                else:
                    revert = True

                # Call method to change product and revert prices
                self.change_product_and_revert_prices(product_id=item_data['product'], quote_item=quote_item,
                                                      revert=revert)

                # If price in request is different from current quote item price, update the price
                if quote_item.price != price_as_decimal:
                    self.update_price(price=price_as_decimal, product_id=item_data['product'], quote_item=quote_item,
                                      product_changed=True)
                # Mark changes as true
                changes = True
            else:
                # If product id from request matches with current quote item
                if quote_item.price != price_as_decimal:
                    # If price is different, update the price
                    self.update_price(price=price_as_decimal, product_id=item_data['product'], quote_item=quote_item)
                    # Mark changes as true
                    changes = True

                if quote_item.quantity != quantity_as_integer:
                    # If quantity is different, update the quantity
                    quote_item.quantity = quantity_as_integer
                    # Mark changes as true
                    changes = True

            # If any changes were made, save the updated quote item
            if changes:
                quote_item.save()

        # If quote_file_type is found in request data
        if quote_file_type:
            # If a quote URL already exists for the quote instance, delete the existing file from the storage
            if instance.quote_url:
                delete_s3_object(object_key=instance.s3_quote_key)

            # Update the quote file and get the updated quote and the presigned URL
            quote_and_presigned_url = self.update_quote_file(quote=instance, quote_file_type=quote_file_type)

            # Store the presigned URL in the context for later use
            self.context['presigned_url'] = quote_and_presigned_url['presigned_url']

            # Return the updated quote and presigned URL
            return quote_and_presigned_url['quote']

            # If quote_file_type is not present in request data
        else:
            # Save and return the updated quote instance
            instance.save()
            return instance

    @staticmethod
    def convert_querydict_to_dict(query_dict):
        """
        Converts a query dict to a dictionary.

        :param query_dict: A query dict containing key-value pairs.
        :type query_dict: dict
        :return: The converted dictionary.
        :rtype: dict
        """
        return {
            query_dict.get('supplier', '[]'): query_dict.get('items', '[]')}

    def create_single_quote(self, request_data, quote_file_type=None, manual_creation=False):
        """
                Creates a single quote and optionally uploads a file associated with the quote.

                Args:
                    request_data (dict): A dictionary containing the necessary data to create a quote.
                                         This should include the supplier ID and associated items.
                    quote_file_type (str, optional): The type of the quote file to be uploaded. Defaults to None.
                    manual_creation (bool, optional): A flag indicating whether the quote is being manually created or not (through an automated process such as through a management command).
                                                      If True, updates the price of the product associated with each quote item. Defaults to False.

                Returns:
                    Quote or dict: The created Quote object and, if a file upload was initiated, the presigned URL information for the upload.

                Raises:
                    serializers.ValidationError: If the product with the provided ID does not exist.
                """
        # Parse the supplier id from the request data
        supplier_id = list(request_data.keys())[0]
        # Fetch the supplier object
        supplier = Supplier.objects.get(id=list(request_data.keys())[0])
        # Create a list to hold the email addresses of the supplier
        supplier_emails = [supplier.email]
        # Create an empty list to hold the data that will be emailed to the supplier
        quote_email_data = []

        # Try to fetch the supplier contact email, if exists
        try:
            supplier_contact_email = supplier.supplieruserprofile.user.email
            # Append the supplier contact email to the supplier emails list
            supplier_emails.append(supplier_contact_email)
        except Exception:
            pass

        # Check if a manual quote creation has been initiated
        if manual_creation:
            # Parse the items from the request data
            items = json.loads(request_data[supplier_id])
            # Create a quote with status as 'RECEIVED'
            quote = Quote.objects.create(supplier=supplier, status='RECEIVED')

        # If not manual creation, directly get items from the request_data
        else:
            items = request_data[supplier_id]
            # Create a quote with supplier data
            quote = Quote.objects.create(supplier=supplier)

        # Iterate over each item for quote
        for item in items:
            # Fetch the product_id from item
            product_id = item.pop('product', None)
            # Fetch the catalog number and product's name for the given product_id
            cat_num, product_name = Product.objects.filter(id=product_id).values_list('cat_num', 'name').first()
            # Create a QuoteItem using fetched data
            QuoteItem.objects.create(quote=quote, product_id=product_id, **item)

            # If it was a manual creation, update the price of the product in database
            if manual_creation:
                try:
                    # Fetch product using product_id
                    product = Product.objects.get(id=product_id)
                    # Preserve the current price as previous_price
                    product.previous_price = product.price
                    # Update the price of the product
                    product.price = item['price']
                    # Save the changes made to the product price
                    product.save()
                except Product.DoesNotExist as e:
                    # If product does not exist in database, raise validation error
                    raise serializers.ValidationError(str(e))

            # Prepare quote data to be sent to supplier via email
            quote_email_data.append({'cat_num': f'{cat_num}', 'name': f'{product_name}', 'quantity': item['quantity']})

            # Send an email to supplier with quote data
        self.send_email(quote_email_data, supplier_emails)

        # If quote_file_type exists then update quote file
        if quote_file_type:
            # Pass the quote and quote file type to update the quote file
            quote_and_presigned_url = self.update_quote_file(quote=quote, quote_file_type=quote_file_type)
            return quote_and_presigned_url
        else:
            return quote

    def create_multiple_quote(self, request_data):
        """
            Creates multiple quotes from supplied data.

            The method iterates through the request data where each entry corresponds to a single quote to be created.
            For each quote, a corresponding `Quote` object is created in the database.
            For every quote, corresponding items are created as `QuoteItem` instances.
            An email containing the quote data is then sent to the corresponding suppliers.

            Args:
                request_data (dict): A dictionary containing data needed to create multiple quotes.
                                     Each key-value pair in the dictionary stands for a single quote.
                                     The key is the supplier ID, and the value is a list of items for the quote.

            Returns:
                list: A list of created `Quote` instances.

            """
        # Prepare a list to hold the created quotes
        created_quotes = []

        # Iterate over each supplier_id and corresponding items in request_data
        for (supplier_id, items) in request_data.items():
            # Fetch the supplier object
            supplier = Supplier.objects.get(id=supplier_id)
            # Create a quote with the fetched supplier
            quote = Quote.objects.create(supplier=supplier)
            # Prepare a list to hold the email addresses of the supplier
            supplier_emails = [supplier.email]
            # Prepare a list to hold the data to be emailed to the supplier
            quote_email_data = []

            # Attempt to fetch the contact email of the supplier and append it to supplier_emails
            try:
                supplier_contact_email = supplier.supplieruserprofile.user.email
                supplier_emails.append(supplier_contact_email)
            except Exception:
                pass

            # Iterate over each item
            for item in items:
                # Fetch the product associated with the item
                product = Product.objects.get(id=int(item['product']))
                # Create a QuoteItem with the fetched product and the current quote
                quote_item = QuoteItem.objects.create(quote=quote, product=product, quantity=item['quantity'])
                # Append relevant data to quote_email_data
                quote_email_data.append(
                    {'cat_num': f'{product.cat_num}', 'name': f'{product.name}', 'quantity': quote_item.quantity})

            # Add the created quote to the created_quotes list
            created_quotes.append(quote)

            # Send an email to the supplier with the quote data
            self.send_email(quote_email_data, supplier_emails)

        # Return the list of created quotes after all quotes have been processed
        return created_quotes

    @staticmethod
    def send_email(email_data, supplier_emails):
        """
        Send an email to a list of suppliers with the given email data.

        :param email_data: A dictionary representing the email data.
        :param supplier_emails: A list of supplier email addresses.
        :return: None
        """
        # Populate 'items' value of context with email_data
        context = {'items': email_data}
        # Convert the email template to a string using the context. 'email_template.html' should be a HTML file located in your templates directory.
        html_message = render_to_string('email_template.html', context)

        # Define the subject of the email
        subject = "הצעת מחיר"
        # Send email using Django's send_mail function.
        # Here 'motdekar@gmail.com' is used as the from email address to send the email
        # All the emails will be sent to the list of supplier_emails
        # The email's body content is provided by html_message
        send_mail(subject, "", 'motdekar@gmail.com', supplier_emails,
                  fail_silently=False,
                  html_message=html_message)

    @staticmethod
    def generate_s3_key(quote, quote_file_type):
        """
        Generate S3 key for a quote file.

        :param quote: The quote object.
        :param quote_file_type: The file type of the quote.
        :return: The generated S3 key.
        """
        # Get the file subtype (for instance "png" from "image/png") from the quote_file_type
        file_type = quote_file_type.split('/')[-1]

        # Create a S3 object key with the naming convention "quotes/supplier_{supplier_name}_quote_{quote_id}.{file_type}"
        s3_object_key = f"quotes/supplier_{quote.supplier.name}_quote_{quote.id}.{file_type}"

        # Return the generated S3 object key
        return s3_object_key

    def update_quote_file(self, quote, quote_file_type):
        """
        Update the quote file.

        :param quote: The quote object to update the file for.
        :param quote_file_type: The file type of the quote file.
        :return: A dictionary containing the updated quote object and presigned URL information.

        """
        # Generate the unique S3 key for the quote file
        s3_object_key = self.generate_s3_key(quote, quote_file_type)

        # Create a pre-signed POST request for uploading a file to S3 bucket
        presigned_post_data = create_presigned_post(object_name=s3_object_key, file_type=quote_file_type)

        # If presigned_post_data is available (not None or empty)
        if presigned_post_data:
            # Create a new FileUploadStatus object with status 'uploading' for the quote file
            upload_status = FileUploadStatus.objects.create(status='uploading', quote=quote)
            # Assign the generated S3 key to the quote object's `s3_quote_key` field
            quote.s3_quote_key = s3_object_key
            # Save the changes made to the quote object
            quote.save()

        # Assign presigned POST request URL and fields to the presigned_url dictionary
        presigned_url = {
            'url': presigned_post_data['url'],
            'fields': presigned_post_data['fields'],
            'key': s3_object_key,
        }

        # Return the updated quote object along with the presigned URL for the S3 upload operation
        return {'quote': quote, 'presigned_url': presigned_url}

    @staticmethod
    def change_product_and_revert_prices(product_id, quote_item, revert):
        """
        Change the product associated with a quote item and revert the prices if specified.

        :param product_id: The ID of the new product to associate with the quote item.
        :param quote_item: The quote item object to update.
        :param revert: A boolean flag indicating whether to revert the prices or not.
        :return: None
        """
        # If True, retrieve the product currently associated with the quote_item
        try:
            wrong_product = Product.objects.get(id=quote_item.product_id)
        except Product.DoesNotExist as e:
            # If wrong_product doesn't exist, raise a validation error
            raise serializers.ValidationError(str(e))

        # Revert price of the old/wrong product to the previous one
        wrong_product.price = wrong_product.previous_price
        # Save changes made to the wrong_product
        wrong_product.save()

        # Update the product associated with the quote_item, regardless of whether the 'revert' flag is set or not
        quote_item.product_id = product_id

    @staticmethod
    def update_price(price, product_id, quote_item, product_changed=False):
        """
        Updates the price of a product and a quote item.

        :param price: The new price value.
        :type price: float
        :param product_id: The ID of the product to update.
        :type product_id: int
        :param quote_item: The quote item to update the price for.
        :type quote_item: QuoteItem
        :param product_changed: Indicates whether the product has changed. Default is False.
        :type product_changed: bool
        :return: None
        :rtype: None

        :raises serializers.ValidationError: If the product with the given ID does not exist.
        """
        try:
            # Attempt to retrieve the product object from the database using the provided product_id
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist as e:
            # If the product doesn't exist in the database, raise a validation error
            raise serializers.ValidationError(str(e))

        if product_changed:
            # If the product has been changed, assign the current price of the product to previous_price attribute
            product.previous_price = product.price

            # Update the price of the product
        product.price = price
        # Save the changes made to the product instance
        product.save()

        # Update the price of the quote item
        quote_item.price = price
