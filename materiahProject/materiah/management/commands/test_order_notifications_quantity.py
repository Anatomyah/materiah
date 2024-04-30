from django.core.management import BaseCommand
from django.db import transaction

from ...models import Product, OrderNotifications, ProductOrderStatistics
from ...tasks import refresh_order_notifications


class QuantityCommand(BaseCommand):
    """
    This command is used to set mock order quantity statistics for the first 5 products in the database,
    then it refreshes order notifications and prints those related to the 5 products.
    """

    # Brief description of the command which will show up on the command overview
    help = 'Sets mock order quantity statistics for the first 5 products and refreshes order notifications'

    def handle(self, *args, **options):
        try:
            # Start database transaction to ensure database integrity even if something goes wrong
            with transaction.atomic():
                # Fetch top 5 products from the database
                products = Product.objects.all()[:5]

                for product in products:
                    # Fetch associated ProductOrderStatistics record or create a new one if it doesn't exist
                    product_stats, created = ProductOrderStatistics.objects.get_or_create(product=product)

                    # Set avg_order_quantity field to a specific number
                    mock_avg_quantity = 20
                    product_stats.avg_order_quantity = mock_avg_quantity

                    # Save changes to the database
                    product_stats.save()

                # Refresh order notifications after setting mock order quantity statistics
                refresh_order_notifications()

                # Fetch IDs of fetched Product objects
                product_ids = [product.id for product in products]
                # Fetch all order notifications associated with fetched Product objects
                order_notifications = OrderNotifications.objects.filter(product_id__in=product_ids)

                # Print order notifications and a success message
        except Exception as e:
            # Print the details of any exceptions that were raised during execution
            print(f'An error occurred: {e}')
