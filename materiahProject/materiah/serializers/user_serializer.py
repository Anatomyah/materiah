from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from ..models import Supplier
from ..models.user import User, UserProfile, SupplierUserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_prefix', 'phone_suffix']


class SupplierUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierUserProfile
        fields = ['contact_phone_prefix', 'contact_phone_suffix']


class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='id', read_only=True)
    password = serializers.CharField(write_only=True)
    userprofile = UserProfileSerializer(required=True)
    supplieruserprofile = SupplierUserProfileSerializer(required=False)
    supplier_data = serializers.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        super(UserSerializer, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['userprofile'] = UserProfileSerializer(self.instance.userprofile, required=True)
            if hasattr(self.instance, 'supplieruserprofile'):
                self.fields['supplieruserprofile'] = SupplierUserProfileSerializer(self.instance.supplieruserprofile,
                                                                                   required=False)

    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'password', 'userprofile',
                  'supplieruserprofile', 'supplier_data']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        try:
            profile = instance.userprofile
            rep['phone_prefix'] = profile.phone_prefix
            rep['phone_suffix'] = profile.phone_suffix
            rep.pop('userprofile', None)
        except ObjectDoesNotExist:
            pass

        try:
            supplier_profile = instance.supplieruserprofile
            rep['supplier_id'] = supplier_profile.supplier.id
            rep['supplier_name'] = supplier_profile.supplier.name
            rep['supplier_phone_prefix'] = supplier_profile.supplier.phone_prefix
            rep['supplier_phone_suffix'] = supplier_profile.supplier.phone_suffix
            rep['supplier_email'] = supplier_profile.supplier.email
            rep['supplier_website'] = supplier_profile.supplier.website
            rep['phone_prefix'] = supplier_profile.contact_phone_prefix
            rep['phone_suffix'] = supplier_profile.contact_phone_suffix
            rep['is_supplier'] = True
            rep.pop('supplieruserprofile', None)
        except ObjectDoesNotExist:
            pass

        return rep

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)

        if self.instance:
            internal_value['supplier_data'] = data.get('supplier_data', '')

        return internal_value

    def create(self, validated_data):
        profile_data = validated_data.pop('userprofile', None)
        password = validated_data.get('password')

        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        user = User.objects.create_user(**validated_data)

        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('userprofile', None)
        supplier_profile_data = validated_data.pop('supplieruserprofile', None)
        supplier_data = validated_data.pop('supplier_data', None)

        if profile_data:
            try:
                profile, created = UserProfile.objects.get_or_create(user=instance)
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError("User Profile does not exist")

            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        if supplier_profile_data:
            try:
                supplier_profile, created = SupplierUserProfile.objects.get_or_create(user=instance)
            except SupplierUserProfile.DoesNotExist:
                raise serializers.ValidationError("Supplier User Profile does not exist")

            for attr, value in supplier_profile_data.items():
                setattr(supplier_profile, attr, value)
            supplier_profile.save()

            try:
                supplier = Supplier.objects.get(id=supplier_data.pop('supplier_id'))
            except Supplier.DoesNotExist:
                raise serializers.ValidationError("Supplier does not exist")

            for attr, value in supplier_data.items():
                setattr(supplier, attr, value)
            supplier.save()

        updated_instance = super().update(instance, validated_data)

        refetched_instance = User.objects.get(id=updated_instance.id)

        return refetched_instance
