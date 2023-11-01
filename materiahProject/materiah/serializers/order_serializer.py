import json

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .product_serializer import ProductSerializer
from .quote_serializer import QuoteSerializer
from ..models import Quote, QuoteItem, OrderNotifications, ProductOrderStatistics, Product, Order, OrderItem, OrderImage


class OrderImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(allow_empty_file=False, use_url=True)

    class Meta:
        model = OrderImage
        fields = ['id', 'image', 'alt_text']


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
    images_read = OrderImageSerializer(source='orderimage_set', many=True, read_only=True)
    images_write = serializers.ListField(
        child=OrderImageSerializer(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Order
        fields = ['id', 'quote', 'arrival_date', 'items', 'images_read', 'images_write', 'received_by']

    def to_representation(self, instance):
        rep = super(OrderSerializer, self).to_representation(instance)
        rep['supplier'] = {'id': instance.quote.supplier.id, 'name': instance.quote.supplier.name}
        rep['quote'] = QuoteSerializer(instance.quote, context=self.context).data
        rep['images'] = rep.pop('images_read', [])
        return rep

    def to_internal_value(self, data):
        internal_value = super(OrderSerializer, self).to_internal_value(data)
        if 'images' in data:
            internal_value['images_write'] = data.get('images')
        return internal_value

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

        images_data = self.context.get('view').request.FILES
        self.handle_images(images_data, order)

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

        self.check_and_delete_images(instance=instance)

        images_data = self.context.get('view').request.FILES
        if images_data:
            self.handle_images(images_data, instance)

        return instance

    def check_and_delete_images(self, instance):
        images_to_keep_ids = self.context.get('view').request.data.get('images_to_keep', None)
        images_to_keep_ids = [int(id_) for id_ in images_to_keep_ids.split(',')] if images_to_keep_ids else None

        if images_to_keep_ids:
            instance.orderimage_set.exclude(id__in=images_to_keep_ids).delete()

    def handle_images(self, images_data, order_instance):
        try:
            for image_data in images_data.values():
                self.process_images(image_data, order_instance)
        except (ValueError, OSError, AttributeError) as e:
            raise serializers.ValidationError(f"An error occurred while processing the image: {e}")

    @staticmethod
    def process_images(image_data, order_instance):
        timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S')
        custom_file_name = f"order_{order_instance.id}_{timestamp_str}.jpg"
        image_data.name = custom_file_name
        OrderImage.objects.create(product=order_instance, image=image_data)

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
            raise serializers.ValidationError(f"Product with CAT# {cat_num} does not exist")

        inventory_product, created = Product.objects.get_or_create(
            cat_num=cat_num,
            supplier_cat_item=False,
            defaults={
                'name': catalogue_product.name,
                'category': catalogue_product.category,
                'unit': catalogue_product.unit,
                'volume': catalogue_product.volume,
                'stock': 0,
                'storage': catalogue_product.storage,
                'price': catalogue_product.price,
                'url': catalogue_product.url,
                'manufacturer': catalogue_product.manufacturer,
                'supplier': catalogue_product.supplier
            }
        )

        if created and update_stock:
            inventory_product.stock = quantity
            inventory_product.save()

        if not created:
            OrderSerializer.delete_notification(inventory_product)
            OrderSerializer.update_product_statistics_and_quantity_on_create(product=inventory_product,
                                                                             quantity=quantity,
                                                                             update_stock=update_stock)

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
