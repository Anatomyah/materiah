from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Supplier
from ..models.manufacturer import Manufacturer, ManufacturerSupplier
from ..models.product import Product

"""
   Serializer for the Manufacturer model. It includes fields to handle relationships with
   Suppliers and Products.

   The serializer handles custom serialization for 'suppliers' and 'products' fields and
   custom create and update methods to manage Manufacturer-Supplier relationships.

   Attributes:
       suppliers (SerializerMethodField): A field to represent the suppliers associated with the manufacturer.
       products (SerializerMethodField): A field to represent the products provided by the manufacturer.

   Meta:
       model: The Manufacturer model that is being serialized.
       fields: Fields to include in the serialized output.
   """


class ManufacturerSerializer(serializers.ModelSerializer):
    suppliers = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'website', 'products', 'suppliers']

    def to_internal_value(self, data):
        """
                Overrides the default to_internal_value method to handle the 'suppliers' field in the incoming data.

                This method processes the incoming data before it is used to create or update a Manufacturer instance.
                It specifically handles the 'suppliers' field which is expected to be a comma-separated string of supplier IDs.

                Process:
                    1. Inherits the default behavior for converting incoming data to a Python dictionary.
                    2. Parses the 'suppliers' field, which should be a comma-separated string of supplier IDs,
                       and converts it into a list of integers.
                    3. Handles ValueError if the conversion process fails, indicating invalid supplier data.

                Args:
                    data (dict): The incoming data to be processed.

                Returns:
                    dict: The processed data with the 'suppliers' field as a list of integers.

                Raises:
                    serializers.ValidationError: If the 'suppliers' field contains invalid data (non-numeric values).
                """
        internal_value = super().to_internal_value(data)

        try:
            internal_value['suppliers'] = [int(id_str) for id_str in data.get('suppliers', '').split(',') if id_str]
            return internal_value
        except ValueError:
            raise serializers.ValidationError({"Suppliers": "Invalid supplier information provided"})

    @staticmethod
    def get_suppliers(obj):
        qs = Supplier.objects.filter(manufacturersupplier__manufacturer=obj)
        return [{'id': supplier.id, 'name': supplier.name, 'website': supplier.website} for supplier in qs]

    @staticmethod
    def get_products(obj):
        qs = Product.objects.filter(manufacturer=obj)
        return [{'id': product.id, 'name': product.name, 'cat_num': product.cat_num} for product in qs]

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
            raise serializers.ValidationError(str(e))

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


"""
Serializer for the ManufacturerSupplier model. This model serves as an intermediary
in a many-to-many relationship between the Manufacturer and Supplier models.

The serializer uses `PrimaryKeyRelatedField` for both 'manufacturer' and 'supplier'
fields to represent the relationships. It allows the API to handle these relationships
via primary keys.

Attributes:
    manufacturer (PrimaryKeyRelatedField): A field to represent the manufacturer in the relationship.
        It references the Manufacturer model and allows selection from all manufacturer instances.
    supplier (PrimaryKeyRelatedField): A field to represent the supplier in the relationship.
        It references the Supplier model and allows selection from all supplier instances.

Meta:
    model: The ManufacturerSupplier model that is being serialized.
    fields: Fields ('manufacturer', 'supplier') to include in the serialized output.
"""


class ManufacturerSupplierSerializer(serializers.ModelSerializer):
    manufacturer = serializers.PrimaryKeyRelatedField(queryset=Manufacturer.objects.all())
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())

    class Meta:
        model = ManufacturerSupplier
        fields = ('manufacturer', 'supplier')
