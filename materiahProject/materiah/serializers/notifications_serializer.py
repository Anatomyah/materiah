from rest_framework import serializers
from ..models import OrderNotifications, ExpiryNotifications


class OrderNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderNotifications
        fields = [
            'product',
        ]

    def to_representation(self, instance):
        """
        :param instance: The instance of the object that needs to be represented.

        :return: The representation of the object.
        """
        representation = super(OrderNotificationSerializer, self).to_representation(instance)

        product = instance.product
        representation['product'] = {
            'id': product.id,
            'name': product.name,
            'cat_num': product.cat_num,
            'supplier': {'id': product.supplier.id, 'name': product.supplier.name},
            'current_stock': product.stock,
            'last_ordered': product.productorderstatistics.last_ordered,
            'avg_order_time': product.productorderstatistics.avg_order_time,
            'avg_order_quantity': product.productorderstatistics.avg_order_quantity

        }
        return representation


class ExpiryNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpiryNotifications
        fields = ['product_item']

    def to_representation(self, instance):
        """
        :param instance: The instance of the object that needs to be represented.

        :return: The representation of the object.
        """
        representation = super(ExpiryNotificationSerializer, self).to_representation(instance)

        product_item = instance.product_item
        representation['product_item'] = {
            'product_item': {'id': product_item.id, 'batch': product_item.batch, 'in_use': product_item.in_use,
                             'expiry': product_item.expiry},
            'product': {'id': product_item.product.id, 'name': product_item.product.name,
                        'cat_num': product_item.product.cat_num},
            'order': {'order', product_item.order_item.order.id, 'received', product_item.order_item.order.arrival_date}

        }
        return representation
