import pytz
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Calculate order statistics for the last 24 hours.'

    def handle(self, *args, **kwargs):
        print('timezone.now()', timezone.now())
        print('timezone.datetime.now()', timezone.datetime.now())
        print(type(timezone.datetime.now()))
        local_timezone = pytz.timezone(settings.TIME_ZONE)
        current_time = timezone.datetime.now()
        current_time = local_timezone.localize(current_time)
        print('current_time', current_time)
        print(type(current_time))
