from rest_framework import serializers
from ..models import OrderNotifications, ExpiryNotifications, supplier
from ..tasks import timedelta_to_str


class OrderNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderNotifications
        fields = ['id', 'product']

    def to_representation(self, instance):
        """
        :param instance: An instance of OrderNotificationSerializer.
        :return: The representation of the given instance.

        This method takes an instance of OrderNotificationSerializer and returns its representation. The
        representation includes information about the product associated with the instance, such as its ID, name,
        catalog number, supplier information, current stock, last ordered date, average order time, and average order
        quantity.


        """
        representation = super(OrderNotificationSerializer, self).to_representation(instance)

        product = instance.product
        representation['product'] = {
            'id': product.id,
            'name': product.name,
            'cat_num': product.cat_num,
            'supplier': {'id': product.supplier.id, 'name': product.supplier.name},
            'current_stock': product.stock,
            'last_ordered': product.productorderstatistics.last_ordered.strftime(
                '%d-%m-%Y') if product.productorderstatistics.last_ordered is not None else None,
            'avg_order_time': timedelta_to_str(
                product.productorderstatistics.avg_order_time) if product.productorderstatistics.avg_order_time is not None else None,
            'avg_order_quantity': product.productorderstatistics.avg_order_quantity

        }
        return representation


class ExpiryNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpiryNotifications
        fields = ['id', 'product_item']

    def to_representation(self, instance):
        """
        :param instance: an instance of the ExpiryNotificationSerializer class
        :return: the representation of the instance

        This method takes an instance of the ExpiryNotificationSerializer class and returns its representation. The
        representation is obtained by calling the `to_representation` method of the parent class (super) and
        modifying it.

        The `product_item` attribute of the instance is extracted and added to the representation.
        The `product_item` dictionary is updated with the following keys:
        - 'id': the ID of the product item
        - 'batch': the batch of the product item
        - 'in_use': the in use status of the product item
        - 'expiry': the expiry date of the product item
        - 'product': a dictionary containing information about the product item's product
            - 'id': the ID of the product
            - 'name': the name of the product
            - 'cat_num': the catalog number of the product
            - 'supplier': the ID of the supplier of the product
        - 'order': a dictionary containing information about the order item associated with the product item
            - 'id': the ID of the order
            - 'received': the arrival date of the order

        Finally, the modified representation is returned.
        """
        representation = super(ExpiryNotificationSerializer, self).to_representation(instance)

        product_item = instance.product_item
        representation['product_item'] = {
            'id': product_item.id, 'batch': product_item.batch, 'in_use': product_item.in_use,
            'expiry': product_item.expiry,
            'product': {'id': product_item.product.id, 'name': product_item.product.name,
                        'cat_num': product_item.product.cat_num, 'supplier': product_item.product.supplier.id},
        }

        # If the product is related to an order, add it to the representation
        if product_item.order_item:
            representation['product_item']['order'] = {'id': product_item.order_item.order.id,
                                                       'received': product_item.order_item.order.arrival_date}

        return representation
