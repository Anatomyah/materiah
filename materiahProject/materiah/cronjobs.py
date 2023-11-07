from django.utils import timezone
from datetime import timedelta

from .models import ProductOrderStatistics, OrderNotifications
from .models.file import FileUploadStatus


def timedelta_to_str(td):
    total_seconds = td.total_seconds()

    years, total_seconds = divmod(total_seconds, 31536000)
    months, total_seconds = divmod(total_seconds, 2592000)
    days, _ = divmod(total_seconds, 86400)

    time_units = [
        (int(years), 'year', 'years'),
        (int(months), 'month', 'months'),
        (int(days), 'day', 'days'),
    ]

    return ', '.join(
        f"{count} {singular if count == 1 else plural}"
        for count, singular, plural in time_units
        if count > 0
    )


def refresh_order_notifications():
    relevant_products = ProductOrderStatistics.objects.filter(avg_order_time__isnull=False)
    current_time = timezone.now()

    OrderNotifications.objects.all().delete()

    for product_stats in relevant_products:
        if product_stats.avg_order_time < (current_time - product_stats.last_ordered):
            product = product_stats.product
            string_repr = timedelta_to_str(product_stats.avg_order_time)
            OrderNotifications.objects.create(
                product=product,
                product_name=product.name,
                product_cat_num=product.cat_num,
                supplier_name=product.supplier.name,
                current_stock=product.stock,
                last_ordered=product_stats.last_ordered.date(),
                avg_order_time=string_repr
            )

            print(f'Created a new notification for product {product.id}')

    print('Successfully recalculated and refreshed order statistics.')


def delete_failed_upload_statuses():
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    upload_statuses = FileUploadStatus.objects.filter(created_at__lt=ten_minutes_ago)

    if upload_statuses:
        upload_statuses.delete()

    print("Finished cleaning upload statuses")


def create_file_upload_status_test_instance():
    new_status = FileUploadStatus.objects.create(status='pending')
