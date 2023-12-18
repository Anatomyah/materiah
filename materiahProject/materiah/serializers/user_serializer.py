from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from ..models import Supplier
from ..models.user import User, UserProfile, SupplierUserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
       Serializer for UserProfile model.

       UserProfileSerializer is a subclass of ModelSerializer that provides a default set of fields and simple default implementations of create() and update() methods.

       The UserProfileSerializer has a field-set that closely mirrors the UserProfile model. In addition to the automatically generated fields, no additional fields are specified manually.
       """

    class Meta:
        model = UserProfile
        fields = ['phone_prefix', 'phone_suffix']


class SupplierUserProfileSerializer(serializers.ModelSerializer):
    """
        Serializer for SupplierUserProfile model.

        Similarly to UserProfileSerializer, SupplierUserProfileSerializer is a subclass of ModelSerializer.
        It provides serialization and validation functionality for SupplierUserProfile instances based on the existing model fields.

        The SupplierUserProfileSerializer has a field-set that closely mirrors the SupplierUserProfile model.
        In addition to the automatically generated fields, no additional fields are specified manually.
        """

    class Meta:
        model = SupplierUserProfile
        fields = ['contact_phone_prefix', 'contact_phone_suffix']


class UserSerializer(serializers.ModelSerializer):
    """
      Serializer class for User model.

      Serializer for User model that provides fields and methods for operations such as create and update.
      This class uses related serializers(UserProfileSerializer and SupplierUserProfileSerializer) to handle complicated writable nested representations.

      UserSerializer also redefines certain fields for the User model such as `password` where it is set to write only to not expose sensitive user information.

      It includes Supplier data as a JSON field and overrides some methods such as to_representation and to_internal_value to better suit the needs of the application.

      Attributes:
          user_id: An IntegerField that represents the 'id' field of the User model.
          password: A CharField that represents the 'password' field of the User model, set to write_only to ensure security.
          userprofile: An instance of UserProfileSerializer representing the related UserProfile of the user.
          supplieruserprofile: An optional instance of SupplierUserProfileSerializer representing the related SupplierUserProfile, if the user is also a supplier.
          supplier_data :  JSONField for storing supplier related data.
      """
    user_id = serializers.IntegerField(source='id', read_only=True)
    password = serializers.CharField(write_only=True)
    userprofile = UserProfileSerializer(required=True)
    supplieruserprofile = SupplierUserProfileSerializer(required=False)
    supplier_data = serializers.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        # Call the parent serializer's __init__ method
        super(UserSerializer, self).__init__(*args, **kwargs)

        # Check if the serializer instance is being initialized for update.
        # 'self.instance' would be None for 'create' operations.
        if self.instance:
            # Update the 'userprofile' field to use an instance of UserProfileSerializer
            # with the related UserProfile object for the User 'self.instance'
            # This ensures correct serialization of existing 'userprofile' data.
            self.fields['userprofile'] = UserProfileSerializer(self.instance.userprofile, required=True)

            # Check if the User instance has a related SupplierUserProfile object.
            if hasattr(self.instance, 'supplieruserprofile'):
                # Update the 'supplieruserprofile' field to use an instance of SupplierUserProfileSerializer
                # with the related SupplierUserProfile object for the User 'self.instance'
                # This ensures correct serialization of existing 'supplieruserprofile' data.
                self.fields['supplieruserprofile'] = SupplierUserProfileSerializer(self.instance.supplieruserprofile,
                                                                                   required=False)

    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'password', 'userprofile',
                  'supplieruserprofile', 'supplier_data']

    def to_representation(self, instance):
        """
        :param instance: The instance of a model.
        :return: The representation of the instance with additional fields.

        This method is used to customize the representation of an instance. It extends the super().to_representation()
        method by adding additional fields to the representation if they exist in the instance. If the fields do not exist,
        they are ignored.
        """
        rep = super().to_representation(instance)
        try:
            # Try to access the UserProfile associated with 'instance'
            profile = instance.userprofile
            # Add each field of the UserProfile as a separate field in the representation
            rep['phone_prefix'] = profile.phone_prefix
            rep['phone_suffix'] = profile.phone_suffix
            # Remove the 'userprofile' field from the representation,
            # as its fields have already been added separately
            rep.pop('userprofile', None)
        except ObjectDoesNotExist:
            # If the user has no associated UserProfile, this block does nothing and
            # the function continues to the next block
            pass

        try:
            # Try to access the SupplierUserProfile associated with 'instance'
            supplier_profile = instance.supplieruserprofile
            # Manually fill in the data from the supplier to the representation
            rep['supplier_id'] = supplier_profile.supplier.id
            rep['supplier_name'] = supplier_profile.supplier.name
            rep['supplier_phone_prefix'] = supplier_profile.supplier.phone_prefix
            rep['supplier_phone_suffix'] = supplier_profile.supplier.phone_suffix
            rep['supplier_email'] = supplier_profile.supplier.email
            rep['supplier_website'] = supplier_profile.supplier.website
            # Since there is a SupplierUserProfile, this user is a supplier
            rep['is_supplier'] = True
            # Remove the 'supplieruserprofile' field from the representation,
            # as its fields have been already added separately
            rep.pop('supplieruserprofile', None)
        except ObjectDoesNotExist:
            # If the 'instance' does not have a SupplierUserProfile, this block silently fails/rescues
            # exception and the function continues
            pass

        # Return the final representation after adding all the necessary fields to it
        return rep

    def to_internal_value(self, data):
        """
        :param data: The data to be processed and converted to internal value.
        :return: The internal value representation of the data.

        This method takes in a data parameter and processes it to obtain the internal value representation.
        It first calls the parent class's to_internal_value method to handle the common processing.
        If there is an existing instance, it assigns the value of the 'supplier_data' key in the data dictionary to the 'supplier_data' key in the internal_value dictionary.
        The updated internal_value is then returned.
        """
        internal_value = super().to_internal_value(data)

        # Check if the serializer instance is being initialized for update.
        # 'self.instance' would be None for 'create' operations.
        if self.instance:
            # If there's existing 'supplier_data' in the incoming data, add it to the internal_value dictionary,
            # otherwise add an empty string as the 'supplier_data'.
            # This step is important since 'supplier_data' is not part of the regular User model fields,
            # and therefore is not handled by the parent serializer's to_internal_value method.
            internal_value['supplier_data'] = data.get('supplier_data', '')

        # Return the internal value which will be used to create or update the model instance
        return internal_value

    def create(self, validated_data):
        """

        Create a new user with the given validated data.

        :param validated_data: A dictionary containing the validated data for creating a user.
        :type validated_data: dict
        :return: The created user object.
        :rtype: User

        """
        # 'pop' the 'userprofile' key-value pair from validated_data, defaulting to None if it does not exist in validated_data
        # 'profile_data' will be used to create a UserProfile for the new User
        profile_data = validated_data.pop('userprofile', None)

        # Extract the password from the validated data.
        # Note that 'password' will be removed from validated_data when calling create_user
        password = validated_data.get('password')

        try:
            # Validate the password using Django's built-in password validation.
            # Will raise a ValidationError if the password is not valid
            validate_password(password)
        except ValidationError as e:
            # Raise a serializers.ValidationError if the password is not valid
            # The error messages are attached to the 'password' field
            raise serializers.ValidationError({'password': e.messages})

        # Create a user. The fields for the new user are filled with the rest of the validated data (excluding 'profile_data')
        # The password is hashed by the create_user method
        user = User.objects.create_user(**validated_data)

        if profile_data:
            # If 'profile_data' was included in the original data, create a UserProfile for the new user
            UserProfile.objects.create(user=user, **profile_data)

        # Return the created user instance
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        :param instance: The instance to be updated.
        :param validated_data: The data to be used for updating the instance.
        :return: The refetched instance after updating.

        This method updates the given instance using the provided validated data. It also updates related user profiles and supplier profiles if present in the validated data. It returns the
        * refetched instance after the update.
        """
        # Using 'pop' to extract profile data from validated data to separate dictionary
        profile_data = validated_data.pop('userprofile', None)
        # Using 'pop' to extract supplier profile data from validated data to separate dictionary
        supplier_profile_data = validated_data.pop('supplieruserprofile', None)
        # Using 'pop' to extract and separate the supplier data from the rest of the data
        supplier_data = validated_data.pop('supplier_data', None)

        # Check and process profile data if available
        if profile_data:
            try:
                # Try to get the UserProfile object for the user instance, if it does not exist, it is created
                profile, created = UserProfile.objects.get_or_create(user=instance)
            except UserProfile.DoesNotExist:
                # Raise validation error if instance does not exist
                raise serializers.ValidationError("User Profile does not exist")

            # Update the attributes of user profile with profile data
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        # Check and process supplier profile data if available
        if supplier_profile_data:
            try:
                # Try to get the SupplierUserProfile object for the user instance, if it does not exist, it is created
                supplier_profile, created = SupplierUserProfile.objects.get_or_create(user=instance)
            except SupplierUserProfile.DoesNotExist:
                # Raise validation error if instance does not exist
                raise serializers.ValidationError("Supplier User Profile does not exist")

            # Update supplier's attributes with new data
            for attr, value in supplier_profile_data.items():
                setattr(supplier_profile, attr, value)
            supplier_profile.save()

            # Update supplier's data if available
            if supplier_data:
                # If supplier data is available, update supplier using this data
                try:
                    # Get the Supplier object for updating
                    supplier = Supplier.objects.get(id=supplier_data.pop('supplier_id'))
                except Supplier.DoesNotExist:
                    # Raise validation error if instance does not exist
                    raise serializers.ValidationError("Supplier does not exist")

                # Update the supplier's attributes with new data
                for attr, value in supplier_data.items():
                    setattr(supplier, attr, value)
                supplier.save()

        # Call the parent serializer's update method to handle the non-profile fields
        updated_instance = super().update(instance, validated_data)

        # Refetch the updated user instance for the latest database data
        refetched_instance = User.objects.get(id=updated_instance.id)

        # Return the refetched and updated user instance
        return refetched_instance
