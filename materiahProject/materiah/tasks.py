from django.utils import timezone
from datetime import timedelta

from .models import ProductOrderStatistics, OrderNotifications
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
        This function refreshes order notifications based on product statistics.
        """

    # Fetch all ProductOrderStatistics objects whose avg_order_time field is not null
    relevant_products = ProductOrderStatistics.objects.filter(avg_order_time__isnull=False)

    # Get the current time
    current_time = timezone.now()

    # Delete all existing OrderNotifications
    OrderNotifications.objects.all().delete()

    # Iterate over each relevant_product
    for product_stats in relevant_products:
        # If the average order time is less than the time elapsed since the product was last ordered
        if product_stats.avg_order_time < (current_time - product_stats.last_ordered):
            # Extract product related to the product_stat
            product = product_stats.product

            # Convert timedelta to string (e.g. "1 day, 5 months, 2 years")
            string_repr = timedelta_to_str(product_stats.avg_order_time)

            # Create a new OrderNotification object
            OrderNotifications.objects.create(
                product=product,
                product_name=product.name,  # Name of the product
                product_cat_num=product.cat_num,  # Catalog number of the product
                supplier_name=product.supplier.name,  # Name of the supplier
                current_stock=product.stock,  # Current stock of the product
                last_ordered=product_stats.last_ordered.date(),  # Date when the product was last ordered
                avg_order_time=string_repr  # String representation of average order time
            )


def delete_failed_upload_statuses():
    """
        This function deletes FileUploadStatus instances that were created more than 10 minutes ago.
        """

    # Calculate timestamp for 10 minutes ago
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)

    # Get all FileUploadStatus objects that were created before ten_minutes_ago
    upload_statuses = FileUploadStatus.objects.filter(created_at__lt=ten_minutes_ago)

    # Check if there are any FileUploadStatus instances to delete
    if upload_statuses:
        # If yes, delete these object instances
        upload_statuses.delete()

    # The function does not return a value. It's intentionally made to just perform the deletion operation.
