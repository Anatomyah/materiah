from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Supplier
from ..models.manufacturer import Manufacturer, ManufacturerSupplier
from ..models.product import Product


class ManufacturerSerializer(serializers.ModelSerializer):
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
        """
        This method retrieves the suppliers associated with a given manufacturer.

        Args:
            obj (Manufacturer): The manufacturer instance.

        Returns:
            list: A list of dictionaries where each dictionary contains the id, name, and website of a supplier associated with the manufacturer.
        """
        qs = Supplier.objects.filter(manufacturersupplier__manufacturer=obj)
        # Return a list of dictionaries where each dictionary contains information about a supplier (id, name, and website)
        return [{'id': supplier.id, 'name': supplier.name, 'website': supplier.website} for supplier in qs]

    @staticmethod
    def get_products(obj):
        """
            This method retrieves the products made by a given manufacturer.

            Args:
                obj (Manufacturer): The manufacturer instance.

            Returns:
                list: A list of dictionaries where each dictionary contains the id, name, and cat_num of a product made by the manufacturer.
            """
        qs = Product.objects.filter(manufacturer=obj)
        # Return a list of dictionaries where each dictionary contains information about a product (id, name, and cat_num)
        return [{'id': product.id, 'name': product.name, 'cat_num': product.cat_num} for product in qs]

    def create(self, validated_data):
        """
          This method creates a manufacturer instance and associated supplier instances.

          Args:
              validated_data (dict): A dictionary of validated data necessary for creating a manufacturer and supplier instances.

          Returns:
              manufacturer (Manufacturer): The created manufacturer instance.

          Raises:
              serializers.ValidationError: Raised when there are validation issues like the manufacturer name already exists, etc.

          This method starts a database transaction and tries to create a Manufacturer and associated suppliers. If this
          operation fails due to the reasons like an IntegrityError (which happens if the manufacturer with the same name
          already exists), a ValidationError or any other exception, it rolls back the changes and raises a validation error.
          """
        try:
            # Begin an atomic transaction to ensure database integrity
            with transaction.atomic():
                # Pop the supplier ids from the validated data if they exist
                supplier_ids = validated_data.pop('suppliers', [])
                # Create the manufacturer instance with remaining validated data
                manufacturer = Manufacturer.objects.create(**validated_data)

                # Bulk create ManufacturerSupplier relationships using the previously popped supplier ids
                ManufacturerSupplier.objects.bulk_create([
                    ManufacturerSupplier(manufacturer=manufacturer, supplier_id=supplier_id) for supplier_id in
                    supplier_ids
                ])

            # After successful creation, return the manufacturer instance
            return manufacturer

        # Handle exceptions and related validation errors
        except IntegrityError:
            # If the manufacturer name already exists, raise a validation error
            raise serializers.ValidationError({"name": "Manufacturer with this name already exists"})
        except ValidationError as e:
            # If there are any other validation errors, raise a validation error with the message from the original error
            raise serializers.ValidationError(str(e))
        except Exception as e:
            # If there are any other unhandled exceptions, raise a generic validation error with the message from the original exception
            raise serializers.ValidationError(str(e))

    def update(self, instance, validated_data):
        """
            This method updates a manufacturer instance and its associated supplier instances .

            Args:
                instance (Manufacturer): A manufacturer instance to be updated.
                validated_data (dict): A dictionary of validated data which contains update information.

            Returns:
                instance (Manufacturer): The updated manufacturer instance.

            Raises:
                serializers.ValidationError: Raised when there are validation issues like the manufacturer name already exists, or any unexpected error occurs.

            This method starts a database transaction to ensure the database remains consistent even if an error occurs during the update. It updates the manufacturer and the related suppliers. If there is any exception, it raises a validation error.
            """
        try:
            # Begin an atomic transaction to ensure database integrity
            with transaction.atomic():
                # Pop the supplier ids from the validated data if they exist
                supplier_ids = validated_data.pop('suppliers', [])

                # Update the instance's name and website from the validated data or leave the old value if not given new one
                instance.name = validated_data.get('name', instance.name)
                instance.website = validated_data.get('website', instance.website)

                # Save the updated manufacturer instance to the database
                instance.save()

            # Remove all current ManufacturerSupplier relationships for the manufacturer
            instance.manufacturersupplier_set.all().delete()

            # Bulk create new ManufacturerSupplier relationships with the previously popped supplier ids
            ManufacturerSupplier.objects.bulk_create([
                ManufacturerSupplier(manufacturer=instance, supplier_id=supplier_id) for supplier_id in supplier_ids
            ])

            # Return the updated manufacturer instance
            return instance

        # Handle exceptions and related validation errors
        except IntegrityError:
            # If the manufacturer name already exists, raise a validation error
            raise serializers.ValidationError({"name": "Manufacturer with this name already exists"})
        except ValidationError as e:
            # If there are any other validation errors, raise a validation error with the message from the original error
            raise serializers.ValidationError(str(e))
        except Exception as e:
            # If there are any other unhandled exceptions, raise a generic validation error with the original exception message
            raise serializers.ValidationError("An unexpected error occurred")


class ManufacturerSupplierSerializer(serializers.ModelSerializer):
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
    manufacturer = serializers.PrimaryKeyRelatedField(queryset=Manufacturer.objects.all())
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())

    class Meta:
        model = ManufacturerSupplier
        fields = ('manufacturer', 'supplier')
