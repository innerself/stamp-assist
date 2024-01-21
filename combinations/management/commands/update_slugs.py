from django.core.management import BaseCommand

from combinations.models import StampSample


class Command(BaseCommand):
    def handle(self, *args, **options):
        StampSample.objects.update_slugs()
