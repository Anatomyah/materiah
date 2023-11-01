from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from ..models import Manufacturer, Supplier
from ..models.product import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(allow_empty_file=False, use_url=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text']


class ProductSerializer(serializers.ModelSerializer):
    images_read = ProductImageSerializer(source='productimage_set', many=True, read_only=True)
    images_write = serializers.ListField(
        child=ProductImageSerializer(),
        required=False,
        write_only=True
    )

    manufacturer = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'cat_num', 'name', 'category', 'unit', 'volume', 'stock',
            'storage', 'price', 'url', 'manufacturer', 'supplier', 'images_read', 'images_write', 'supplier_cat_item'
        ]

    @staticmethod
    def get_manufacturer(obj):
        return {
            'id': obj.manufacturer.id,
            'name': obj.manufacturer.name,
        }

    @staticmethod
    def get_supplier(obj):
        return {
            'id': obj.supplier.id,
            'name': obj.supplier.name,
        }

    def to_representation(self, instance):
        representation = super(ProductSerializer, self).to_representation(instance)
        representation['images'] = representation.pop('images_read', [])
        return representation

    def to_internal_value(self, data):
        internal_value = super(ProductSerializer, self).to_internal_value(data)
        if 'images' in data:
            internal_value['images_write'] = data.get('images')
        return internal_value

    @staticmethod
    def validate_cat_num(value):
        if not value:
            raise serializers.ValidationError("Product CAT #: This field is required.")
        return value

    @staticmethod
    def validate_name(value):
        if not value:
            raise serializers.ValidationError("Product name: This field is required.")
        return value

    @staticmethod
    def validate_category(value):
        if not value:
            raise serializers.ValidationError("Category: This field is required.")
        return value

    @staticmethod
    def validate_volume(value):
        if not value:
            raise serializers.ValidationError("Volume: This field is required.")
        return value

    @staticmethod
    def validate_storage(value):
        if not value:
            raise serializers.ValidationError("Storage: This field is required.")
        return value

    @staticmethod
    def validate_url(value):
        if not value:
            raise serializers.ValidationError("Product url: This field is required.")
        return value

    @staticmethod
    def validate_manufacturer(value):
        if not value:
            raise serializers.ValidationError("Manufacturer: This field is required.")
        return value

    @staticmethod
    def validate_supplier(value):
        if not value:
            raise serializers.ValidationError("Supplier: This field is required.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        manufacturer_id = self.context.get('view').request.data.get('manufacturer')
        supplier_id = self.context.get('view').request.data.get('supplier')
        validated_data['supplier_cat_item'] = self.context.get('view').request.data.get('supplier_cat_item') == 'true'

        try:
            manufacturer = Manufacturer.objects.get(id=manufacturer_id)
        except Manufacturer.DoesNotExist:
            raise serializers.ValidationError("Manufacturer does not exist")
        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            raise serializers.ValidationError("Supplier does not exist")

        product = Product.objects.create(manufacturer=manufacturer,
                                         supplier=supplier, **validated_data)

        images_data = self.context.get('view').request.FILES
        if images_data:
            self.handle_images(images_data, product)

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        self.check_and_delete_images(instance=instance)

        images_data = self.context.get('view').request.FILES
        if images_data:
            self.handle_images(images_data, instance)

        return instance

    def check_and_delete_images(self, instance):
        images_to_keep_ids = self.context.get('view').request.data.get('images_to_keep', None)
        images_to_keep_ids = [int(id_) for id_ in images_to_keep_ids.split(',')] if images_to_keep_ids else None

        if images_to_keep_ids:
            instance.productimage_set.exclude(id__in=images_to_keep_ids).delete()

    def handle_images(self, images_data, product_instance):
        try:
            for image_data in images_data.values():
                self.process_images(image_data, product_instance)
        except (ValueError, OSError, AttributeError) as e:
            raise serializers.ValidationError(f"An error occurred while processing the image: {e}")

    @staticmethod
    def process_images(image_data, product_instance):
        timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S')
        custom_file_name = f"product_{product_instance.id}_{timestamp_str}.jpg"
        image_data.name = custom_file_name
        ProductImage.objects.create(product=product_instance, image=image_data)
