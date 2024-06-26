from django.core.management.base import BaseCommand

from ...models import StockItem, ExpiryNotifications


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
            ExpiryNotifications.objects.create(product_item_id=272)
            expiry_notifications = ExpiryNotifications.objects.all()
            for expiry_notification in expiry_notifications:
                product_item = StockItem.objects.get(id=expiry_notification.product_item_id)
                if not product_item.expired:
                    print('no product')

        except Exception as e:
            print(f'An error occurred: {e}')
