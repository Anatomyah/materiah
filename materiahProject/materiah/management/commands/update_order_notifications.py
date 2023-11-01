from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from materiah.models import ProductOrderStatistics, OrderNotifications


class Command(BaseCommand):
    help = 'Calculate order statistics for the last 24 hours.'

    @staticmethod
    def timedelta_to_str(td: timedelta) -> str:
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

    def handle(self, *args, **kwargs):
        relevant_products = ProductOrderStatistics.objects.filter(avg_order_time__isnull=False)
        current_time = timezone.now()

        OrderNotifications.objects.all().delete()

        for product_stats in relevant_products:
            if product_stats.avg_order_time < (current_time - product_stats.last_ordered):
                product = product_stats.product
                string_repr = self.timedelta_to_str(product_stats.avg_order_time)
                OrderNotifications.objects.create(
                    product=product,
                    product_name=product.name,
                    product_cat_num=product.cat_num,
                    supplier_name=product.supplier.name,
                    current_stock=product.stock,
                    last_ordered=product_stats.last_ordered.date(),
                    avg_order_time=string_repr
                )

                self.stdout.write(
                    self.style.SUCCESS(f'Created a new notification for product {product.id}'))

        self.stdout.write(self.style.SUCCESS('Successfully recalculated and refreshed order statistics.'))
