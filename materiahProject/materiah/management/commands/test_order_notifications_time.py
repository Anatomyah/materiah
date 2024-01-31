import datetime

from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone

from ...models import Product, OrderNotifications, ProductOrderStatistics
from ...tasks import refresh_order_notifications


class TimeCommand(BaseCommand):
    """
    This command is used to set mock order time statistics for the first 5 products in the database.
    It sets the `last_ordered` field to a specific date, and `avg_order_time` field to a specific duration.
    """

    # Brief description of the command which will show up on the command overview
    help = 'Sets mock order time statistics for the first 5 products'

    def handle(self, *args, **options):
        try:
            # Start database transaction to ensure database integrity even if something goes wrong
            with transaction.atomic():
                # Fetch top 5 products from the database
                products = Product.objects.all()[:5]

                for product in products:
                    # Fetch associated ProductOrderStatistics record or create one if it does not exist
                    product_stats, created = ProductOrderStatistics.objects.get_or_create(product=product)

                    # Set last_ordered field to a specific past date
                    mock_last_ordered_date = timezone.make_aware(datetime.datetime(2022, 1, 1, 1, 23, 59, 59))
                    product_stats.last_ordered = mock_last_ordered_date

                    # Set avg_order_time field to a specific duration(days)
                    mock_avg_order_time = datetime.timedelta(weeks=10)
                    product_stats.avg_order_time = mock_avg_order_time

                    # Save changes into the database
                    product_stats.save()

                    # Fetch IDs of fetched products
                    product_ids = [product.id for product in products]

                    # Fetch all OrderNotifications associated with fetched products
                    order_notifications = OrderNotifications.objects.filter(product_id__in=product_ids)
                    print(order_notifications)

                print('Successfully created order time statistics')
        except Exception as e:
            # Print the details of any exceptions that were raised during execution
            print(f'An error occurred: {e}')
