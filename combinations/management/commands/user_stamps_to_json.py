import json
from pathlib import Path

from django.core.management import BaseCommand

from accounts.models import User
from combinations.models import UserStamp


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        user = User.objects.get(username=options['username'])
        with open(Path(options['path']), 'w') as f:
            json.dump(UserStamp.objects.filter(user=user).to_json(), f)
