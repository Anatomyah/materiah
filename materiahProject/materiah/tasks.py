from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import ProductOrderStatistics, OrderNotifications, ProductItem, ExpiryNotifications
from .models.file import FileUploadStatus


def timedelta_to_str(td):
    """
       This function converts a timedelta object into a human-readable string format.
       """

    # Extract total seconds from given timedelta object
    total_seconds = td.total_seconds()

    # Convert total_seconds into years, months, and days
    years, total_seconds = divmod(total_seconds, 31536000)
    months, total_seconds = divmod(total_seconds, 2592000)
    days, _ = divmod(total_seconds, 86400)

    # Prepare a list of tuples where each tuple consists of count of a unit of time (year/month/day),
    # its singular form ('year'/'month'/'day') and its plural form ('years'/'months'/'days')
    time_units = [
        (int(years), 'year', 'years'),
        (int(months), 'month', 'months'),
        (int(days), 'day', 'days'),
    ]

    # Create a human-readable string. It joins each non-zero count and its respective unit in
    # singular form if count==1 else plural form. For example: "1 day, 5 months, 2 years"
    return ', '.join(
        f"{count} {singular if count == 1 else plural}"
        for count, singular, plural in time_units
        if count > 0
    )


def refresh_order_notifications():
    """
    Refreshes order notifications by performing the following steps:
    1. Fetch all ProductOrderStatistics objects whose avg_order_time and avg_order_quantity fields are not null
    2. Get the current time
    3. Delete all existing OrderNotifications
    4. Iterate over each relevant_product
        - Extract the product related to the product_stat
        - If the relevant values needed to perform the calculation meet certain conditions:
            - Create a new OrderNotification object for the product
    """

    # Fetch all ProductOrderStatistics objects whose avg_order_time and avg_order_quantity fields are not null
    relevant_products = ProductOrderStatistics.objects.filter(
        Q(avg_order_time__isnull=False) | Q(avg_order_quantity__isnull=False)
    )
    # Get the current time
    current_time = timezone.now()

    # Delete all existing OrderNotifications
    OrderNotifications.objects.all().delete()

    # Iterate over each relevant_product
    for product_stats in relevant_products:
        # Extract product related to the product_stat
        product = product_stats.product

        # If the relevant values needed to perform the calculation exist and the average order time is less than the
        # time elapsed since the product was last ordered or if half of the average order quantity for this product
        # is more than it's current stock
        if ((product_stats.avg_order_time is not None and product_stats.last_ordered is not None and
             (product_stats.avg_order_time < (current_time - product_stats.last_ordered))) or
                (product_stats.avg_order_quantity is not None and product.stock is not None and
                 (product_stats.avg_order_quantity / 2) > product.stock)):
            # Create a new OrderNotification object
            OrderNotifications.objects.create(product=product)


def create_expiry_notifications():
    """
    Creates expiry notifications for relevant stock items.

    This method filters the ProductItems to only those items whose expiry date precedes the current date or falls
    within the next six months. It then iterates through each of the relevant stock items and creates expiry
    notifications for them.

    :return: None
    """
    current_date = timezone.now().date()
    expiry_date = current_date + timedelta(days=180)

    # Filter the ProductItem to only those items which expiry date precedes the current date or falls within the next
    # six months
    relevant_stock_items = ProductItem.objects.filter(
        Q(expiry__range=(current_date, expiry_date)) | Q(expiry__lt=current_date) & Q(expirynotifications__isnull=True))

    # Iterate through each of the relevant stock items and create and create expiry notifications for them
    for item in relevant_stock_items:
        ExpiryNotifications.objects.create(product_item=item)


def delete_failed_upload_statuses():
    """
        This function deletes FileUploadStatus instances that were created more than 20 minutes ago.
        """

    # Calculate timestamp for 20 minutes ago
    twenty_minutes_ago = timezone.now() - timedelta(minutes=20)

    # Get all FileUploadStatus objects that were created before twenty_minutes_ago
    upload_statuses = FileUploadStatus.objects.filter(created_at__lt=twenty_minutes_ago)

    # Check if there are any FileUploadStatus instances to delete
    if upload_statuses:
        # If yes, delete these object instances
        upload_statuses.delete()
