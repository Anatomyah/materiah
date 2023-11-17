import json
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .product_serializer import ProductSerializer
from .quote_serializer import QuoteSerializer
from ..s3 import create_presigned_post, delete_s3_object
from ..models import Quote, QuoteItem, OrderNotifications, ProductOrderStatistics, Product, Order, OrderItem, OrderImage
from ..models.file import FileUploadStatus

"""
    Serializer for the OrderImage model. This serializer handles the serialization
    and deserialization of OrderImage instances.

    Meta:
        model: The OrderImage model that is being serialized.
        fields: Specifies the 'id' and 'image_url' fields to include in the serialized output.
    """


class OrderImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderImage
        fields = ['id', 'image_url']


"""
    Serializer for the OrderItem model. It handles serialization and deserialization
    of OrderItem instances, including custom representation of related models.

    In the to_representation method, it adds a serialized representation of related
    Product and specific details of the QuoteItem associated with the OrderItem.

    Meta:
        model: The OrderItem model that is being serialized.
        fields: Specifies fields to include in the serialized output.

    Methods:
        to_representation: Overrides the default method to add 'product' and 'quote_item'
        information to the serialized representation.
    """


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'quantity', 'batch', 'expiry', 'status', 'issue_detail']

    def to_representation(self, instance):
        """
               Overrides the default to_representation method to add additional data.

               This method enhances the default serialized representation by including
               a nested representation of the related Product and specific details of
               the QuoteItem associated with this OrderItem.

               Args:
                   instance (OrderItem): The OrderItem instance being serialized.

               Returns:
                   dict: The serialized representation of the OrderItem, including additional data.
               """
        rep = super(OrderItemSerializer, self).to_representation(instance)
        rep['product'] = ProductSerializer(instance.quote_item.product).data
        rep['quote_item'] = {'id': instance.quote_item.id, 'quantity': instance.quote_item.quantity}
        return rep


"""
Serializer for the Order model. This serializer handles serialization and deserialization
of Order instances, including nested representations of order items and images.

Attributes:
    items (OrderItemSerializer): A nested serializer for order items, linked via the 'orderitem_set' relation.
    quote (PrimaryKeyRelatedField): A field representing the quote associated with the order. Write-only.
    images (OrderImageSerializer): A nested read-only serializer for order images, linked via the 'orderimage_set' relation.

Meta:
    model: The Order model that is being serialized.
    fields: Specifies fields to include in the serialized output.

Methods:
    to_representation: Overrides the default method to add additional data,
                        including supplier info and serialized quote.
"""


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, required=False)
    quote = serializers.PrimaryKeyRelatedField(queryset=Quote.objects.all(), write_only=True)
    images = OrderImageSerializer(source='orderimage_set', many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'quote', 'arrival_date', 'items', 'images', 'received_by']

    def to_representation(self, instance):
        """
               Overrides the default to_representation method to add additional data.

               This method enhances the default serialized representation by including
               supplier information and a nested representation of the associated quote.
               It also handles the custom formatting for images.

               Args:
                   instance (Order): The Order instance being serialized.

               Returns:
                   dict: The serialized representation of the Order, including additional data.
               """
        rep = super(OrderSerializer, self).to_representation(instance)
        rep['supplier'] = {'id': instance.quote.supplier.id, 'name': instance.quote.supplier.name}
        rep['quote'] = QuoteSerializer(instance.quote, context=self.context).data
        rep['images'] = rep.pop('images', [])
        return rep

    @transaction.atomic
    def create(self, validated_data):
        """
        Creates an Order instance along with associated business logic. This method handles:
        - Creating the Order based on the related quote and other validated data.
        - Processing each item in the order, including inventory updates and quote item fulfillment.
        - Checking if the entire quote is fulfilled based on the order items.
        - Handling image data associated with the order, including generating presigned URLs.

        Args:
            validated_data (dict): The validated data from the incoming request used to create the order.

        Returns:
            Order: The newly created Order instance.

        Raises:
            json.JSONDecodeError: If there is an error in parsing the JSON data for items or images.
        """

        request = self.context.get('request', None)
        items_data = json.loads(request.data.get('items', '[]'))

        related_quote = validated_data.pop('quote')
        order = Order.objects.create(quote=related_quote, **validated_data)
        quote_fulfilled = True

        for item_data in items_data:
            status = item_data['status'] == 'OK' or 'Different amount'
            product_cat_num = item_data.pop('cat_num')

            self.create_inventory_product_or_update_statistics_and_quantity(cat_num=product_cat_num,
                                                                            quantity=item_data['quantity'],
                                                                            update_stock=status)

            quote_item_fulfilled = self.relate_quoteitem_to_orderitem_and_check_quote_fulfillment_create(
                item_data=item_data,
                order=order)

            if not quote_item_fulfilled and quote_fulfilled:
                quote_fulfilled = False

        self.is_quote_fulfilled(related_quote=related_quote, quote_fulfilled=quote_fulfilled)

        try:
            images = json.loads(self.context.get('view').request.data.get('images') or '[]')
        except json.JSONDecodeError:
            images = []

        if images:
            presigned_urls = self.handle_images(images, order)
            self.context['presigned_urls'] = presigned_urls

        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        """
              Updates an existing Order instance along with associated business logic. This method handles:
              - Updating the Order instance with new validated data.
              - Processing each item in the order for updates, including checking quote item fulfillment.
              - Checking if the entire quote is fulfilled based on the updated order items.
              - Handling image data associated with the order, including generating presigned URLs and deleting images.

              Args:
                  instance (Order): The existing Order instance to be updated.
                  validated_data (dict): The validated data from the incoming request used for updating the order.

              Returns:
                  Order: The updated Order instance.

              Raises:
                  json.JSONDecodeError: If there is an error in parsing the JSON data for items or images.
              """
        request = self.context.get('request', None)
        items_data = json.loads(request.data.get('items', '[]'))

        instance.arrival_date = validated_data.get('arrival_date', instance.arrival_date)
        instance.received_by = validated_data.get('received_by', instance.received_by)

        related_quote = validated_data.pop('quote')
        instance.quote = related_quote
        quote_fulfilled = True

        for item_data in items_data:
            quote_item_fulfilled = self.relate_quoteitem_to_orderitem_and_check_quote_fulfillment_update(
                item_data=item_data, instance=instance)

            if not quote_item_fulfilled and quote_fulfilled:
                quote_fulfilled = False

        self.is_quote_fulfilled(related_quote=related_quote, quote_fulfilled=quote_fulfilled)

        images_to_delete = self.context.get('view').request.data.get('images_to_delete')
        if images_to_delete:
            self.check_and_delete_images(images_to_delete)

        try:
            images = json.loads(self.context.get('view').request.data.get('images') or '[]')
        except json.JSONDecodeError:
            images = []

        if images:
            presigned_urls = self.handle_images(images, instance)
            self.context['presigned_urls'] = presigned_urls

        return instance

    @staticmethod
    def check_and_delete_images(image_ids):
        """
            Deletes OrderImage instances and their corresponding files from S3 based on provided image IDs.

            Args:
                image_ids (str): A string of comma-separated image IDs.

            This method parses the image_ids string to get individual image IDs, retrieves each OrderImage instance,
            and deletes the image from S3. If the deletion from S3 is successful, the OrderImage instance is also deleted.
            """
        images_to_delete_ids = [int(id_) for id_ in image_ids.split(',')]
        for image_id in images_to_delete_ids:
            image = OrderImage.objects.get(id=image_id)
            if delete_s3_object(object_key=image.s3_image_key):
                image.delete()

    def handle_images(self, images, order_instance):
        """
           Handles image uploads by generating presigned URLs for S3 and creating corresponding OrderImage instances.

           Args:
               images (list): A list of dictionaries, each containing image data.
               order_instance (Order): The Order instance to which the images are related.

           Returns:
               list: A list of dictionaries containing presigned URL data and image IDs.

           This method generates a unique S3 key for each image, creates a presigned POST data for S3 upload,
           and creates an OrderImage instance and a FileUploadStatus instance for each image. It returns data
           necessary for the frontend to complete the upload process.
           """
        presigned_urls_and_image_ids = []

        for image in images:
            s3_object_key = self.generate_s3_key(order_instance, image['type'])

            presigned_post_data = create_presigned_post(object_name=s3_object_key, file_type=image['type'])

            if presigned_post_data:
                order_image = OrderImage.objects.create(order=order_instance, s3_image_key=s3_object_key)
                upload_status = FileUploadStatus.objects.create(status='uploading', order_receipt=order_image)

                presigned_urls_and_image_ids.append({
                    'url': presigned_post_data['url'],
                    'fields': presigned_post_data['fields'],
                    'key': s3_object_key,
                    'frontend_id': image['id'],
                    'image_id': order_image.id
                })
            else:
                raise serializers.ValidationError("Failed to generate presigned POST data for S3 upload.")

        return presigned_urls_and_image_ids

    @staticmethod
    def generate_s3_key(order, image_type):
        """
            Generates a unique S3 object key for an order image.

            Args:
                order (Order): The Order instance to which the image is related.
                image_type (str): The content type of the image.

            Returns:
                str: A unique S3 object key for the image.

            This method generates a unique S3 key for an order image, using the order ID, image count,
            a unique UUID, and the image type.
            """
        order_image_count = (order.orderimage_set.count()) + 1
        image_type = image_type.split('/')[-1]
        unique_uuid = uuid.uuid4()
        s3_object_key = f"orders/order_{order.id}_image_{order_image_count}_{unique_uuid}.{image_type}"

        return s3_object_key

    @staticmethod
    def delete_notification(product):
        """
            Deletes the OrderNotification instance for a given product.

            Args:
                product (Product): The product for which the notification is to be deleted.

            Raises:
                serializers.ValidationError: If the notification for the given product does not exist.
            """
        try:
            notification = OrderNotifications.objects.get(product=product)
            notification.delete()
        except OrderNotifications.DoesNotExist:
            pass

    @staticmethod
    def update_product_statistics_and_quantity_on_create(product, quantity, update_stock):
        """
           Updates the statistics and stock quantity of a product when an order is created.

           Args:
               product (Product): The product whose statistics and stock quantity are to be updated.
               quantity (int): The quantity of the product ordered.
               update_stock (bool): Flag to determine if the product stock needs to be updated.

           This method updates the order count, average order time, last ordered time, and stock
           for a product based on the new order. It creates a new ProductOrderStatistics instance if it does not exist.
           """
        try:
            product_statistics = product.productorderstatistics
        except ProductOrderStatistics.DoesNotExist:
            product_statistics = ProductOrderStatistics.objects.create(product=product)

        product_statistics.order_count += 1
        updated_order_count = product_statistics.order_count
        current_time = timezone.now()

        if updated_order_count > 1:
            new_delta = current_time - product_statistics.last_ordered
            prev_avg = product_statistics.avg_order_time if updated_order_count > 2 else new_delta
            new_avg = (prev_avg * (updated_order_count - 1) + new_delta) / updated_order_count
            product_statistics.avg_order_time = new_avg
            product_statistics.last_ordered = current_time
        else:
            product_statistics.last_ordered = current_time

        if update_stock:
            product.stock += int(quantity)
            product.save()

        product_statistics.save()

    @staticmethod
    def update_product_stock_on_update(product, new_quantity, quote_item_quantity):
        """
           Updates the stock of a product when an order item is updated.

           Args:
               product (Product): The product whose stock is to be updated.
               new_quantity (int): The new quantity of the product.
               quote_item_quantity (int): The original quantity of the product in the quote item.

           This method adjusts the stock of the product based on the difference between the new quantity
           and the original quote item quantity.
           """
        if quote_item_quantity != new_quantity:
            stock_adjustment = new_quantity - quote_item_quantity
            product.stock += stock_adjustment
        product.save()

    @staticmethod
    def create_inventory_product_or_update_statistics_and_quantity(cat_num, quantity, update_stock):
        """
           Creates or updates an inventory product based on a catalogue product and updates its statistics and quantity.

           Args:
               cat_num (str): The catalog number of the product.
               quantity (int): The quantity of the product ordered.
               update_stock (bool): Flag to indicate whether to update the stock of the product.

           Returns:
               Product: The created or updated inventory product instance.

           This method looks up a catalogue product by its catalog number, and either creates a new inventory product
           or updates the existing one with the same catalog number. It also updates the product's statistics and quantity.
           """
        try:
            catalogue_product = Product.objects.get(cat_num=cat_num, supplier_cat_item=True)
        except Product.DoesNotExist:
            catalogue_product = None

        defaults = {}
        if catalogue_product:
            defaults = {
                'name': catalogue_product.name,
                'category': catalogue_product.category,
                'unit': catalogue_product.unit,
                'volume': catalogue_product.volume,
                'storage': catalogue_product.storage,
                'price': catalogue_product.price,
                'url': catalogue_product.url,
                'manufacturer': catalogue_product.manufacturer,
                'supplier': catalogue_product.supplier
            }

        inventory_product, created = Product.objects.get_or_create(
            cat_num=cat_num,
            supplier_cat_item=False,
            defaults=defaults
        )

        if created and update_stock:
            inventory_product.stock = quantity
            inventory_product.save()

        if not created:
            OrderSerializer.delete_notification(inventory_product)
            OrderSerializer.update_product_statistics_and_quantity_on_create(product=inventory_product,
                                                                             quantity=quantity,
                                                                             update_stock=update_stock)

        return inventory_product

    @staticmethod
    def relate_quoteitem_to_orderitem_and_check_quote_fulfillment_create(item_data, order):
        """
           Relates a quote item to an order item and checks if the quote is fulfilled upon order creation.

           Args:
               item_data (dict): Data dictionary for the order item.
               order (Order): The order to which the item is related.

           Returns:
               bool: True if the quote is fulfilled, False otherwise.

           This method links a QuoteItem to an OrderItem and checks if the quote is fulfilled based on the quantity
           and status of the OrderItem. It raises a validation error if the QuoteItem does not exist.
           """
        try:
            quote_item = QuoteItem.objects.get(id=item_data['quote_item_id'])
        except QuoteItem.DoesNotExist:
            raise serializers.ValidationError(f"Quote item with ID {item_data['quote_item_id']} does not exist")

        order_item = OrderItem.objects.create(order=order, quote_item=quote_item, **item_data)

        product = quote_item.product
        product.price = quote_item.price
        product.save()

        if quote_item.quantity != order_item.quantity or order_item.status != 'OK':
            return False

        return True

    @staticmethod
    def relate_quoteitem_to_orderitem_and_check_quote_fulfillment_update(item_data, instance):
        status = item_data['status'] == 'OK' or 'Different amount'

        try:
            quote_item = QuoteItem.objects.get(id=item_data['quote_item_id'])
        except QuoteItem.DoesNotExist:
            raise serializers.ValidationError(f"Quote item with ID {item_data['quote_item_id']} does not exist")

        order_item = OrderItem.objects.get(order=instance, quote_item=quote_item)

        for field_name, new_value in item_data.items():
            setattr(order_item, field_name, new_value)

        order_item.save()

        product = quote_item.product

        if status:
            OrderSerializer.update_product_stock_on_update(product=product, new_quantity=item_data['quantity'],
                                                           quote_item_quantity=quote_item.quantity)

        if quote_item.quantity != order_item.quantity or order_item.status != 'OK':
            return False

        return True

    @staticmethod
    def is_quote_fulfilled(related_quote, quote_fulfilled):
        if not quote_fulfilled:
            related_quote.status = "ARRIVED, UNFULFILLED"
        else:
            related_quote.status = "FULFILLED"

        related_quote.save()
