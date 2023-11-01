from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Supplier
from ..models.manufacturer import Manufacturer, ManufacturerSupplier
from ..models.product import Product


class ManufacturerSerializer(serializers.ModelSerializer):
    suppliers = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'website', 'products', 'suppliers']

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)

        try:
            internal_value['suppliers'] = [int(id_str) for id_str in data.get('suppliers', '').split(',') if id_str]
        except ValueError:
            raise serializers.ValidationError({"Suppliers": "Invalid supplier information provided"})

        return internal_value

    @staticmethod
    def get_suppliers(obj):
        qs = Supplier.objects.filter(manufacturersupplier__manufacturer=obj)
        return [{'id': supplier.id, 'name': supplier.name} for supplier in qs]

    @staticmethod
    def get_products(obj):
        qs = Product.objects.filter(manufacturer=obj)
        return [{'id': product.id, 'name': product.name, 'cat_num': product.cat_num} for product in qs]

    @staticmethod
    def validate_name(value):
        if not value:
            raise serializers.ValidationError("Manufacturer name: This field is required.")
        return value

    @staticmethod
    def validate_website(value):
        if not value:
            raise serializers.ValidationError("Website url: This field is required.")
        return value

    def create(self, validated_data):
        try:
            with transaction.atomic():
                supplier_ids = validated_data.pop('suppliers', [])
                manufacturer = Manufacturer.objects.create(**validated_data)
                ManufacturerSupplier.objects.bulk_create([
                    ManufacturerSupplier(manufacturer=manufacturer, supplier_id=supplier_id) for supplier_id in
                    supplier_ids
                ])

            return manufacturer
        except IntegrityError:
            raise serializers.ValidationError({"name": "Manufacturer with this name already exists"})
        except ValidationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError("An unexpected error occurred")

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                supplier_ids = validated_data.pop('suppliers', [])

                instance.name = validated_data.get('name', instance.name)
                instance.website = validated_data.get('website', instance.website)
                instance.save()

            instance.manufacturersupplier_set.all().delete()
            ManufacturerSupplier.objects.bulk_create([
                ManufacturerSupplier(manufacturer=instance, supplier_id=supplier_id) for supplier_id in supplier_ids
            ])

            return instance
        except IntegrityError:
            raise serializers.ValidationError({"name": "Manufacturer with this name already exists"})
        except ValidationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError("An unexpected error occurred")


class ManufacturerSupplierSerializer(serializers.ModelSerializer):
    manufacturer = serializers.PrimaryKeyRelatedField(queryset=Manufacturer.objects.all())
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())

    class Meta:
        model = ManufacturerSupplier
        fields = ('manufacturer', 'supplier')
