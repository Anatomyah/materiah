import json
from django.core.mail import send_mail
from django.db import transaction
from django.http import QueryDict
from rest_framework import serializers
from decimal import Decimal

from .product_serializer import ProductSerializer
from ..s3 import create_presigned_post, delete_s3_object
from ..models import Supplier, Product, Order
from ..models.file import FileUploadStatus
from ..models.quote import Quote, QuoteItem


class QuoteItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'quote', 'product', 'quantity', 'price']


class QuoteSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = ['id', 'quote_url', 'supplier', 'request_date', 'creation_date', 'last_updated', 'items',
                  'status', 'order']

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
    def get_order(obj):

        if isinstance(obj, Quote):
            order = Order.objects.filter(quote=obj).first()
            return order.id if order else None
        else:
            order_ids = []
            for quote in obj:
                order = Order.objects.filter(quote=quote).first()
                if order:
                    order_ids.append(order.id)
            return order_ids

    @transaction.atomic
    def create(self, validated_data):
        quote_email_data = {}
        request_data = self.context.get('request').data
        quote_file_type = None
        try:
            quote_file_type = request_data['quote_file_type']
        except Exception as e:
            pass

        if isinstance(request_data, QueryDict):
            request_data = self.convert_querydict_to_dict(request_data)
            if quote_file_type:
                quote_and_presigned_url = self.create_single_quote(quote_email_data=quote_email_data,
                                                                   request_data=request_data,
                                                                   quote_file_type=quote_file_type,
                                                                   manual_creation=True)

                self.context['presigned_url'] = quote_and_presigned_url['presigned_url']
                return quote_and_presigned_url['quote']
            else:
                return self.create_single_quote(quote_email_data=quote_email_data, request_data=request_data,
                                                manual_creation=True)
        if len(request_data.keys()) > 1:
            return self.create_multiple_quote(quote_email_data=quote_email_data, request_data=request_data)
        else:
            return self.create_single_quote(quote_email_data=quote_email_data, request_data=request_data,
                                            quote_file_type=quote_file_type)

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = json.loads(self.context['request'].data.get('items', '[]'))
        quote_file_type = self.context.get('request').data.get('quote_file_type')

        for item_data in items_data:
            price_as_decimal = Decimal(item_data['price'])
            quantity_as_integer = int(item_data['quantity'])
            changes = False
            try:
                quote_item = QuoteItem.objects.get(id=item_data['quote_item_id'])
            except QuoteItem.DoesNotExist as e:
                raise serializers.ValidationError(str(e))

            if quote_item.product_id != item_data['product']:
                if not quote_item.price:
                    revert = False
                else:
                    revert = True

                self.change_product_and_revert_prices(product_id=item_data['product'], quote_item=quote_item,
                                                      revert=revert)

                if quote_item.price != price_as_decimal:
                    self.update_price(price=price_as_decimal, product_id=item_data['product'], quote_item=quote_item,
                                      product_changed=True)

                changes = True
            else:
                if quote_item.price != price_as_decimal:
                    self.update_price(price=price_as_decimal, product_id=item_data['product'], quote_item=quote_item)
                    changes = True

                if quote_item.quantity != quantity_as_integer:
                    quote_item.quantity = quantity_as_integer
                    changes = True

            if changes:
                quote_item.save()

        if quote_file_type:
            delete_s3_object(object_key=instance.s3_quote_key)
            quote_and_presigned_url = self.update_quote_file(quote=instance, quote_file_type=quote_file_type)
            self.context['presigned_url'] = quote_and_presigned_url['presigned_url']

            return quote_and_presigned_url['quote']
        else:
            instance.save()

            return instance

    @staticmethod
    def convert_querydict_to_dict(query_dict):
        return {
            query_dict.get('supplier', '[]'): query_dict.get('items', '[]')}

    def create_single_quote(self, quote_email_data, request_data, quote_file_type=None, manual_creation=False):
        supplier_id = list(request_data.keys())[0]

        if manual_creation:
            items = json.loads(request_data[supplier_id])
            quote = Quote.objects.create(supplier_id=supplier_id, status='RECEIVED')
        else:
            items = request_data[supplier_id]
            quote = Quote.objects.create(supplier_id=supplier_id)

        for item in items:
            product_id = item.pop('product', None)
            cat_num, product_name = Product.objects.filter(id=product_id).values_list('cat_num', 'name').first()
            QuoteItem.objects.create(quote=quote, product_id=product_id, **item)

            if manual_creation:
                try:
                    product = Product.objects.get(id=product_id)
                    product.previous_price = product.price
                    product.price = item['price']
                    product.save()
                except Product.DoesNotExist as e:
                    raise serializers.ValidationError(str(e))

            quote_email_data["single_supplier_0"] = {'cat_num': f'{cat_num}', 'name': f'{product_name}',
                                                     'quantity': item['quantity']}

        self.send_emails(quote_email_data)

        if quote_file_type:
            quote_and_presigned_url = self.update_quote_file(quote=quote, quote_file_type=quote_file_type)
            return quote_and_presigned_url
        else:
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

    @staticmethod
    def generate_s3_key(quote, quote_file_type):
        file_type = quote_file_type.split('/')[-1]
        s3_object_key = f"quotes/supplier_{quote.supplier.name}_quote_{quote.id}.{file_type}"

        return s3_object_key

    def update_quote_file(self, quote, quote_file_type):
        s3_object_key = self.generate_s3_key(quote, quote_file_type)

        presigned_post_data = create_presigned_post(object_name=s3_object_key, file_type=quote_file_type)
        if presigned_post_data:
            upload_status = FileUploadStatus.objects.create(status='uploading', quote=quote)
            quote.s3_quote_key = s3_object_key
            quote.save()

        presigned_url = {
            'url': presigned_post_data['url'],
            'fields': presigned_post_data['fields'],
            'key': s3_object_key,
        }

        return {'quote': quote, 'presigned_url': presigned_url}

    @staticmethod
    def change_product_and_revert_prices(product_id, quote_item, revert):
        if revert:
            try:
                wrong_product = Product.objects.get(id=quote_item.product_id)
            except Product.DoesNotExist as e:
                raise serializers.ValidationError(str(e))

            wrong_product.price = wrong_product.previous_price
            wrong_product.save()

        quote_item.product_id = product_id

    @staticmethod
    def update_price(price, product_id, quote_item, product_changed=False):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist as e:
            raise serializers.ValidationError(str(e))

        if product_changed:
            product.previous_price = product.price
        product.price = price
        product.save()

        quote_item.price = price
