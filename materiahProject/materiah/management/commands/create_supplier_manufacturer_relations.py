from django.core.management.base import BaseCommand

from ...models import Supplier, Manufacturer, ManufacturerSupplier, Product
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
        # Attempt to create a sample product and its necessary items within a transaction
        try:
            products = Product.objects.all()
            for product in products:
                if product.supplier and product.manufacturer:
                    supplier = product.supplier
                    manufacturer = product.manufacturer

                    relationship_exists = ManufacturerSupplier.objects.filter(manufacturer=manufacturer,
                                                                              supplier=supplier).exists()

                    if not relationship_exists:
                        ManufacturerSupplier.objects.create(manufacturer=manufacturer, supplier=supplier)
                        print(f'Relationship created between {manufacturer} and {supplier} for product {product}')

        except Exception as e:
            print(f'An error occurred: {e}')
