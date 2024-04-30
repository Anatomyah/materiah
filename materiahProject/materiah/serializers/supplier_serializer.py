from django.db import transaction
from rest_framework import serializers

from .manufacturer_serializer import ManufacturerSupplier, Manufacturer
from .user_serializer import SupplierUserProfileSerializer
from ..models.product import Product
from ..models.supplier import Supplier, SupplierSecondaryEmails


class SupplierSecondaryEmailsSerializer(serializers.ModelSerializer):
    """
    Serializer for the SupplierSecondaryEmails model.

    :param serializers.ModelSerializer: The base serializer class from the `rest_framework` package.
    """

    class Meta:
        model = SupplierSecondaryEmails
        fields = ['id', 'email']


class SupplierSerializer(serializers.ModelSerializer):
    """
        Serializer class for Supplier model.

        Serializer is a feature in Django REST Framework responsible for converting complex data types from Django
        models into python native data types that can then be easily rendered into JSON. It can also translates
        incoming JSON API payloads into the Python complex types.

        The `SupplierSerializer` class inherits from the `ModelSerializer` class of Django REST Framework to add
        functionality related to the `Supplier` model.

        The `SupplierSerializer` uses `Field` classes such as `SerializerMethodField` and `UserProfileSerializer` to
        represent model fields and perform transformation between model and representation.

        Attributes:
            supplieruserprofile (Serializer): An instance of `SupplierUserProfileSerializer`.
            secondary_emails (Serializer): An instance of `SupplierSecondaryEmailsSerializer`.
            manufacturers (SerializerMethodField): Field that generates manufacturers' data through a provided method.
            products (SerializerMethodField): Field that generates products' data through a provided method.
        """
    supplieruserprofile = SupplierUserProfileSerializer(read_only=True)
    secondary_emails = SupplierSecondaryEmailsSerializer(many=True, read_only=True)
    manufacturers = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'website', 'phone_prefix', 'phone_suffix', 'email', 'secondary_emails',
                  'supplieruserprofile', 'products', 'manufacturers']

    def to_representation(self, instance):
        """
        :param instance: the instance to be converted to representation
        :return: the representation of the instance

        This method converts the given instance to its representation. It calls the superclass method to get the
        initial representation and then checks if the 'supplieruserprofile' key exists in the representation. If it
        exists, it is removed from the representation before returning it.
        """
        rep = super().to_representation(instance)

        if rep.get('supplieruserprofile') is None:
            rep.pop('supplieruserprofile')

        return rep

    def to_internal_value(self, data):
        """
        :param data: The input data to be converted into internal value.
        :return: The converted internal value.

        The `to_internal_value` method is used to convert the input `data` into the internal value. It first calls
        the `super().to_internal_value(data)` method to perform any necessary initial conversion. Then, it extracts
        the 'manufacturers' key from the `data` dictionary and splits the value by ',' delimiter using `data.get(
        'manufacturers', '').split(',')`. It then iterates over the resulting list and converts each element to an
        integer using `int(id_str)`. The resulting list of integers is assigned to the 'manufacturers' key in the
        `internal_value' dictionary. Finally, the `internal_value` dictionary is returned as the converted internal
        value.


        Note: This code assumes the `to_internal_value` method is defined inside a class, as indicated by the use of
        `self` parameter. The `super().to_internal_value(data)` call refers to the * parent class's
        `to_internal_value` method.
        """

        # Retrieve the standard internal value from ModelSerializer's to_internal_value method
        internal_value = super().to_internal_value(data)

        # Convert manufacturer field's value in data, if exists, into a list of integers.
        # The values in the string should be separated by commas.
        # If the string is empty or if manufacturer field does not exist,
        # then an empty list will be assigned to 'manufacturers' in internal_value.
        internal_value['manufacturers'] = [
            int(id_str) for id_str in data.get('manufacturers', '').split(',') if id_str
        ]

        return internal_value

    @staticmethod
    def get_manufacturers(obj):
        """
        Retrieve manufacturers associated with a supplier.

        :param obj: The supplier object.
        :type obj: Supplier
        :return: A list of dictionaries containing manufacturer details.
        :rtype: list[dict]
        """
        # Return a list of dictionaries containing 'id' and 'name' of each manufacturer in the queryset.
        # This transforms the Manufacturer queryset into an easy-to-digest data structure.
        qs = Manufacturer.objects.filter(manufacturersupplier__supplier=obj)
        return [{'id': manufacturers.id, 'name': manufacturers.name} for manufacturers in qs]

    @staticmethod
    def get_products(obj):
        """
        Fetches all products associated with a given supplier.

        :param obj: The supplier object.
        :type obj: Supplier
        :return: A list of dictionaries containing product details.
        :rtype: list
        """
        qs = Product.objects.filter(supplier=obj)
        return [{'id': product.id, 'name': product.name, 'cat_num': product.cat_num} for product in qs]

    @transaction.atomic
    def create(self, validated_data):
        """
        :param validated_data: A dictionary containing validated data for creating a new supplier.
            - The dictionary should include the following keys:
                - 'name': A string representing the name of the supplier.
                - 'address': A string representing the address of the supplier.
                - 'phone': A string representing the phone number of the supplier.
                - 'manufacturers': A list of manufacturer IDs associated with the supplier.
        :return: The newly created supplier object.

        This method creates a new supplier object in the database using the provided validated data.
        It also associates the supplier with the given manufacturer IDs.
        """

        # Extract the list of manufacturer ids from the validated data if it exists,
        # otherwise initialize it as an empty list. The 'pop' method also removes the 'manufacturers'
        # key-value pair from validated_data dictionary.
        manufacturer_ids = validated_data.pop('manufacturers', [])

        # Insert a new Supplier record in the database using the remaining key-value pairs in validated_data
        # as the fields for the new supplier object and store the newly created supplier object.
        supplier = Supplier.objects.create(**validated_data)

        # Fetch the secondary emails list if it exists, else set to None
        secondary_emails = self.context.get('view').request.data.get('secondary_emails', None)

        # If secondary emails were sent, bulk create the required objects
        if secondary_emails:
            SupplierSecondaryEmails.objects.bulk_create(
                [SupplierSecondaryEmails(supplier=supplier, email=email) for email in secondary_emails])

        # The ManufacturerSupplier model is used to denote the many-to-many relationship between Supplier and Manufacturer.
        # Using 'bulk_create' method, create relationships between the new supplier and all the manufacturer
        # IDs we obtained earlier. Create a list with one ManufacturerSupplier object for each manufacturer id in
        # manufacturer_ids list and associate the supplier to every ManufacturerSupplier object.
        ManufacturerSupplier.objects.bulk_create(
            [ManufacturerSupplier(manufacturer_id=manufacturer_id, supplier=supplier) for manufacturer_id in
             manufacturer_ids]
        )
        return supplier

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        :param instance: The instance of the object to be updated.
        :param validated_data: The validated data to update the instance with.
        :return: The updated instance.

        This method updates the given instance with the provided validated data. It uses the transaction.atomic
        decorator to ensure atomicity of the database transaction.

        The method performs the following steps:
        1. Check if the supplier secondary emails need to be deleted or updated
        2. Extracts the manufacturer IDs from the validated data.
        3. Updates the instance with the provided data, if available.
        4. Saves the updated instance.
        5. Deletes all existing ManufacturerSupplier objects associated with the instance.
        6. Bulk creates new ManufacturerSupplier objects with the provided manufacturer IDs and the updated instance.
        """

        # Fetch the secondary emails to delete id's, else set to None
        secondary_emails_to_delete = self.context.get('view').request.data.get('secondary_emails_to_delete', None)

        # If the update requires deletion of secondary email objects, perform the deletion
        if secondary_emails_to_delete:
            for email_id in secondary_emails_to_delete:
                SupplierSecondaryEmails.objects.get(id=email_id).delete()

        #  Fetch the newly added secondary emails, else set to None
        new_secondary_emails = self.context.get('view').request.data.get('secondary_emails', None)

        # If new secondary emails were sent, create them
        if new_secondary_emails:
            for email in new_secondary_emails:
                SupplierSecondaryEmails.objects.create(supplier=instance, email=email)

        # 'pop' the 'manufacturers' key-value pair from validated_data, defaulting to an empty list if it does not
        # exist in validated_data
        manufacturer_ids = validated_data.pop('manufacturers', [])

        # Set the various attributes of 'instance' to their corresponding new values in validated_data,
        # if they exist in validated_data. Otherwise, leave these attributes as they are currently.
        instance.name = validated_data.get('name', instance.name)
        instance.website = validated_data.get('website', instance.website)
        instance.email = validated_data.get('email', instance.email)
        instance.phone_prefix = validated_data.get('phone_prefix', instance.phone_prefix)
        instance.phone_suffix = validated_data.get('phone_suffix', instance.phone_suffix)

        # Save the modified 'instance' to the database
        instance.save()

        # Delete all ManufacturerSupplier objects associated with 'instance'
        instance.manufacturersupplier_set.all().delete()

        # For each manufacturer ID in 'manufacturer_ids', create a ManufacturerSupplier object associating that
        # manufacturer with 'instance'
        ManufacturerSupplier.objects.bulk_create([
            ManufacturerSupplier(manufacturer_id=manufacturer_id, supplier=instance)
            for manufacturer_id in manufacturer_ids
        ])

        return instance
