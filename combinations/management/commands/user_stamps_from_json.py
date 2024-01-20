import json
from pathlib import Path

from django.core.management import BaseCommand

from accounts.models import User
from combinations.models import UserStamp, StampSample, Desk


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        with open(Path(options['path']), 'r') as f:
            data = json.load(f)

        for raw_sample in data:
            user = User.objects.get(username=raw_sample['username'])
            print(f'{raw_sample["sample_slug"] = }')
            sample = StampSample.objects.get(slug=raw_sample['sample_slug'])
            desk = Desk.objects.get(user=user, type=raw_sample['desk_type'])

            UserStamp.objects.create(
                sample=sample,
                custom_name=raw_sample['custom_name'],
                comment=raw_sample['comment'],
                user=user,
                desk=desk,
                allow_repeat=raw_sample['allow_repeat'],
            )
