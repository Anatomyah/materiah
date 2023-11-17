from django.db import transaction
from rest_framework import serializers

from .manufacturer_serializer import ManufacturerSupplier, Manufacturer
from .user_serializer import SupplierUserProfileSerializer
from ..models.product import Product
from ..models.supplier import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    supplieruserprofile = SupplierUserProfileSerializer(read_only=True)
    manufacturers = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'website', 'phone_prefix', 'phone_suffix', 'email', 'supplieruserprofile', 'products',
                  'manufacturers']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep.get('supplieruserprofile') is None:
            rep.pop('supplieruserprofile')

        return rep

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        internal_value['manufacturers'] = [int(id_str) for id_str in data.get('manufacturers', '').split(',') if
                                           id_str]
        return internal_value

    @staticmethod
    def get_manufacturers(obj):
        qs = Manufacturer.objects.filter(manufacturersupplier__supplier=obj)
        return [{'id': manufacturers.id, 'name': manufacturers.name} for manufacturers in qs]

    @staticmethod
    def get_products(obj):
        qs = Product.objects.filter(supplier=obj)
        return [{'id': product.id, 'name': product.name, 'cat_num': product.cat_num} for product in qs]

    @transaction.atomic
    def create(self, validated_data):
        manufacturer_ids = validated_data.pop('manufacturers', [])
        supplier = Supplier.objects.create(**validated_data)
        ManufacturerSupplier.objects.bulk_create([
            ManufacturerSupplier(manufacturer_id=manufacturer_id, supplier=supplier) for manufacturer_id in
            manufacturer_ids
        ])
        return supplier

    @transaction.atomic
    def update(self, instance, validated_data):
        manufacturer_ids = validated_data.pop('manufacturers', [])

        instance.name = validated_data.get('name', instance.name)
        instance.website = validated_data.get('website', instance.website)
        instance.email = validated_data.get('email', instance.email)
        instance.phone_prefix = validated_data.get('phone_prefix', instance.phone_prefix)
        instance.phone_suffix = validated_data.get('phone_suffix', instance.phone_suffix)
        instance.save()

        instance.manufacturersupplier_set.all().delete()

        ManufacturerSupplier.objects.bulk_create([
            ManufacturerSupplier(manufacturer_id=manufacturer_id, supplier=instance)
            for manufacturer_id in manufacturer_ids
        ])

        return instance
