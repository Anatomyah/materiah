from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Description of your command'

    def handle(self, *args, **options):
        pass
