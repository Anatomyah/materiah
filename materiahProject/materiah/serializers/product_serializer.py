import json
import uuid
from django.db import transaction
from rest_framework import serializers

from ..models import Manufacturer, Supplier
from ..models.file import FileUploadStatus
from ..models.product import Product, ProductImage
from .s3 import create_presigned_post, delete_s3_object


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 's3_image_key']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(source='productimage_set', many=True, read_only=True)

    manufacturer = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'cat_num', 'name', 'category', 'unit', 'volume', 'stock',
            'storage', 'price', 'url', 'manufacturer', 'supplier', 'images', 'supplier_cat_item'
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
        representation['images'] = representation.pop('images', [])
        return representation

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
        print(validated_data)
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

        try:
            images = json.loads(self.context.get('view').request.data.get('images') or '[]')
        except json.JSONDecodeError:
            images = []

        if images:
            presigned_urls = self.handle_images(images, product)
            self.context['presigned_urls'] = presigned_urls

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

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
            image = ProductImage.objects.get(id=image_id)
            if delete_s3_object(object_key=image.s3_image_key):
                image.delete()

    def handle_images(self, images, product_instance):
        presigned_urls_and_image_ids = []

        for image in images:
            s3_object_key = self.generate_s3_key(product_instance, image['type'])

            presigned_post_data = create_presigned_post(object_name=s3_object_key, file_type=image['type'])
            if presigned_post_data:
                product_image = ProductImage.objects.create(product=product_instance, s3_image_key=s3_object_key)
                upload_status = FileUploadStatus.objects.create(status='uploading', product_image=product_image)

                presigned_urls_and_image_ids.append({
                    'url': presigned_post_data['url'],
                    'fields': presigned_post_data['fields'],
                    'key': s3_object_key,
                    'frontend_id': image['id'],
                    'image_id': product_image.id
                })
            else:
                raise serializers.ValidationError("Failed to generate presigned POST data for S3 upload.")

        return presigned_urls_and_image_ids

    @staticmethod
    def generate_s3_key(product, image_type):
        product_image_count = (product.productimage_set.count()) + 1
        image_type = image_type.split('/')[-1]
        unique_uuid = uuid.uuid4()
        s3_object_key = f"products/product_{product.id}_image_{product_image_count}_{unique_uuid}.{image_type}"

        return s3_object_key
