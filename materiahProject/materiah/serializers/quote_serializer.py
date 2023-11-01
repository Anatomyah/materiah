import json

from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.http import QueryDict
from rest_framework import serializers

from .product_serializer import ProductSerializer
from ..models import Supplier, Product
from ..models.quote import Quote, QuoteItem


class QuoteItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'quote', 'product', 'quantity', 'price']

    @staticmethod
    def validate_quote(value):
        if not value:
            raise serializers.ValidationError("Quote: This field is required.")
        return value

    @staticmethod
    def validate_product(value):
        if not value:
            raise serializers.ValidationError("Product: This field is required.")
        return value

    @staticmethod
    def validate_quantity(value):
        if not value:
            raise serializers.ValidationError("Quantity: This field is required.")
        return value


class QuoteSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = ['id', 'quote_file', 'supplier', 'request_date', 'creation_date', 'last_updated', 'items',
                  'status']

    @staticmethod
    def get_supplier(obj):
        if isinstance(obj, list):
            return [{'id': supplier.id, 'name': supplier.name} for supplier in Supplier.objects.filter(quote__in=obj)]
        else:
            supplier = Supplier.objects.filter(quote=obj).first()
            return {'id': supplier.id, 'name': supplier.name}

    @staticmethod
    def get_items(obj):
        if isinstance(obj, list):
            return [QuoteItemSerializer(quote.quoteitem_set.all(), many=True).data for quote in obj]
        else:
            return QuoteItemSerializer(obj.quoteitem_set.all(), many=True).data

    @staticmethod
    def get_status(obj):
        if isinstance(obj, list):
            return [item.get_status_display() for item in obj]
        else:
            return obj.get_status_display()

    @staticmethod
    def validate_supplier(value):
        if not value:
            raise serializers.ValidationError("Supplier: This field is required.")
        return value

    @staticmethod
    def quote_file(value):
        if not value:
            raise serializers.ValidationError("Quote file: This field is required.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        quote_email_data = {}
        request_data = self.context.get('request').data
        quote_file = self.context.get('request').FILES.get('quote_file')

        if isinstance(request_data, QueryDict):
            request_data = self.convert_querydict_to_dict(request_data)
            return self.create_single_quote(quote_email_data=quote_email_data, request_data=request_data,
                                            quote_file=quote_file, manual_creation=True)
        if len(request_data.keys()) > 1:
            return self.create_multiple_quote(quote_email_data=quote_email_data, request_data=request_data)
        else:
            return self.create_single_quote(quote_email_data=quote_email_data, request_data=request_data,
                                            quote_file=quote_file)

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = json.loads(self.context['request'].data.get('items', '[]'))
        quote_file = self.context['request'].FILES.get('quote_file')

        if quote_file:
            instance.quote_file.save(quote_file.name, ContentFile(quote_file.read()))
            instance.status = 'RECEIVED'

        for item_data in items_data:
            try:
                product = Product.objects.get(id=item_data.pop('product'))
            except Product.DoesNotExist as e:
                raise serializers.ValidationError(str(e))
            try:
                quote_item = QuoteItem.objects.get(quote=instance, product=product)
            except QuoteItem.DoesNotExist as e:
                raise serializers.ValidationError(str(e))

            product.price = item_data['price']
            quote_item.price = item_data['price']
            product.save()
            quote_item.save()

        instance.save()

        return instance

    @staticmethod
    def convert_querydict_to_dict(query_dict):
        return {
            query_dict.get('supplier', '[]'): query_dict.get('items', '[]')}

    def create_single_quote(self, quote_email_data, request_data, quote_file=None, manual_creation=False):
        supplier_id = list(request_data.keys())[0]
        items = json.loads(request_data[supplier_id])

        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist as e:
            raise serializers.ValidationError(str(e))

        if manual_creation:
            quote = Quote.objects.create(supplier=supplier, status='RECEIVED')
        else:
            quote = Quote.objects.create(supplier=supplier)

        for item in items:
            product_id = item.pop('product', None)
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist as e:
                raise serializers.ValidationError(str(e))

            QuoteItem.objects.create(quote=quote, product=product, **item)
            quote_email_data["single_supplier_0"] = {'cat_num': f'{product.cat_num}', 'name': f'{product.name}',
                                                     'quantity': item['quantity']}

        try:
            if quote_file:
                quote.quote_file.save(quote_file.name, ContentFile(quote_file.read()))
        except IOError as e:
            raise serializers.ValidationError(f"File error: {str(e)}")

        self.send_emails(quote_email_data)

        return quote

    def create_multiple_quote(self, quote_email_data, request_data):
        created_quotes = []
        for counter, (supplier_id, items) in enumerate(request_data.items(), start=1):
            quote = Quote.objects.create(supplier=Supplier.objects.get(id=supplier_id))
            for item in items:
                product = Product.objects.get(id=int(item['product']))
                quote_item = QuoteItem.objects.create(quote=quote, product=product, quantity=item['quantity'])
                quote_email_data[f"multi_supplier_{counter}"] = {'cat_num': f'{product.cat_num}',
                                                                 'name': f'{product.name}',
                                                                 'quantity': quote_item.quantity}
            created_quotes.append(quote)

        self.send_emails(quote_email_data)

        return created_quotes

    @staticmethod
    def send_emails(email_data):
        html_lines = []
        for _, item_data in email_data.items():
            html_line = f"""
                            <div style='text-align: right;'>שם: {item_data['name']}</div>
                            <div style='text-align: right;'>מק\"ט: {item_data['cat_num']}</div>
                            <div style='text-align: right;'>כמות: {item_data['quantity']}</div>
                            """
            html_lines.append(html_line)

        joined_html_lines = ''.join(html_lines)

        html_message = f"""
                            שלום רב,
                            נשמח להצעת מחיר לפריטים הבאים:
                            {joined_html_lines}
                            בברכה,
                            מרכז האורגנואידים
                            """

        subject = "הצעת מחיר"
        send_mail(subject, "", 'motdekar@gmail.com', ['anatomyah@protonmail.com'], fail_silently=False,
                  html_message=html_message)
