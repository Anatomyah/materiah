import json

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .product_serializer import ProductSerializer
from .quote_serializer import QuoteSerializer
from .s3 import create_presigned_post, delete_s3_object
from ..models import Quote, QuoteItem, OrderNotifications, ProductOrderStatistics, Product, Order, OrderItem, OrderImage
from ..models.file import FileUploadStatus


class OrderImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderImage
        fields = ['id', 'image_url']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'quantity', 'batch', 'expiry', 'status', 'issue_detail']

    def to_representation(self, instance):
        rep = super(OrderItemSerializer, self).to_representation(instance)
        rep['product'] = ProductSerializer(instance.quote_item.product).data
        rep['quote_item'] = {'id': instance.quote_item.id, 'quantity': instance.quote_item.quantity}
        return rep


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, required=False)
    quote = serializers.PrimaryKeyRelatedField(queryset=Quote.objects.all(), write_only=True)
    images = OrderImageSerializer(source='orderimage_set', many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'quote', 'arrival_date', 'items', 'images', 'received_by']

    def to_representation(self, instance):
        rep = super(OrderSerializer, self).to_representation(instance)
        rep['supplier'] = {'id': instance.quote.supplier.id, 'name': instance.quote.supplier.name}
        rep['quote'] = QuoteSerializer(instance.quote, context=self.context).data
        rep['images'] = rep.pop('images', [])
        return rep

    @staticmethod
    def validate_quote(value):
        if not value:
            raise serializers.ValidationError("Quote: This field is required.")
        return value

    @staticmethod
    def validate_arrival_date(value):
        if not value:
            raise serializers.ValidationError("Arrival date: This field is required.")
        return value

    @staticmethod
    def validate_receipt_img(value):
        if not value:
            raise serializers.ValidationError("Receipt Image: This field is required.")
        return value

    @staticmethod
    def validate_received_by(value):
        if not value:
            raise serializers.ValidationError("Received by: This field is required.")
        return value

    @transaction.atomic
    def create(self, validated_data):
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
        images_to_delete_ids = [int(id_) for id_ in image_ids.split(',')]
        for image_id in images_to_delete_ids:
            image = OrderImage.objects.get(id=image_id)
            if delete_s3_object(object_key=image.s3_image_key):
                image.delete()

    def handle_images(self, images, order_instance):
        presigned_urls_and_image_ids = []
        counter = 0
        print(images)
        for image in images:
            counter += 1
            print(counter)
            print(image)
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
        order_image_count = (order.orderimage_set.count()) + 1
        image_type = image_type.split('/')[-1]
        s3_object_key = f"orders/order_{order.id}_image_{order_image_count}.{image_type}"

        return s3_object_key

    @staticmethod
    def delete_notification(product):
        try:
            notification = OrderNotifications.objects.get(product=product)
            notification.delete()
        except OrderNotifications.DoesNotExist:
            pass

    @staticmethod
    def update_product_statistics_and_quantity_on_create(product, quantity, update_stock):
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

        if quote_item_quantity != new_quantity:
            stock_adjustment = new_quantity - quote_item_quantity
            product.stock += stock_adjustment
        product.save()

    @staticmethod
    def create_inventory_product_or_update_statistics_and_quantity(cat_num, quantity, update_stock):
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
