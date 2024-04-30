from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Supplier, Product, ProductItem, ExpiryNotifications
from ...tasks import create_expiry_notifications


class Command(BaseCommand):
    """
    This class is a subclass of BaseCommand and represents a custom command in the project.

    Attributes:
        help (str): A string describing the purpose or functionality of the command.

    Methods:
        handle(self, *args, **options): The main entry point for the command. Executes the logic of the command.

    """
    help = 'Creates a sample product with certain product items and their expiry notifications in the project.'

    def handle(self, *args, **options):
        """
                Main entry point for the command. This command attempts to:
                - Create a new product
                - Add product items to the product
                - Refresh expiry notifications for the product items
                - Print the ids of expiry notifications
                - Delete the sample product
                """
        # Attempt to create a sample product and its necessary items within a transaction
        try:
            with transaction.atomic():
                first_supplier = Supplier.objects.first()
                product_items = []

                # Create a new product
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

                # Add product items with a valid expiration date
                for _ in range(2):
                    product_item = ProductItem(
                        product=new_product,
                        batch='notexpired',
                        expiry='2024-12-01'
                    )
                    product_item.save()
                    product_items.append(product_item)

                # Add product items with an invalid expiration date
                for _ in range(2):
                    product_item = ProductItem(
                        product=new_product,
                        batch='expired',
                        expiry='2024-04-01'
                    )
                    product_item.save()
                    product_items.append(product_item)

                # Refresh expiry notifications for the product items
                create_expiry_notifications()

                # Extract product item id's from product items
                product_item_ids = [item.id for item in product_items]

                # Query notifications based on product item ids
                ExpiryNotifications.objects.filter(product_item_id__in=product_item_ids)

                # Delete sample product after creating notifications
                new_product.delete()

        except Exception as e:
            print(f'An error occurred: {e}')
