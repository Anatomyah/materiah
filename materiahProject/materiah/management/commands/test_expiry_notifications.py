from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Supplier, Product, ProductItem, ExpiryNotifications
from ...tasks import refresh_expiry_notifications


class Command(BaseCommand):
    help = 'Description of your command'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                first_supplier = Supplier.objects.first()
                product_items = []
                new_product = Product(
                    cat_num='12345',
                    name='Sample Product',
                    category='Medium',
                    unit='L',
                    unit_quantity=1,
                    stock=10,
                    storage='+4',
                    price=100.00,
                    supplier=first_supplier,
                )
                new_product.save()

                for _ in range(2):
                    product_item = ProductItem(
                        product=new_product,
                        batch='notexpired',
                        expiry='2024-12-01'
                    )
                    product_item.save()
                    product_items.append(product_item)

                for _ in range(2):
                    product_item = ProductItem(
                        product=new_product,
                        batch='expired',
                        expiry='2024-04-01'
                    )
                    product_item.save()
                    product_items.append(product_item)

                refresh_expiry_notifications()

                product_item_ids = [item.id for item in product_items]

                ExpiryNotifications.objects.filter(product_item_id__in=product_item_ids)

                new_product.delete()

                print('Successfully created product, product items, and expiry notifications')
        except Exception as e:
            print(f'An error occurred: {e}')
