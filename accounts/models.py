from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from mimesis import Person, Locale

mim_person_en = Person(locale=Locale.EN)


class UserCustomManager(UserManager):
    def generate(self, **kwargs):
        return self.create(
            username=kwargs.get('username', mim_person_en.username()),
            stamps_min=kwargs.get('stamps_min', 1),
            stamps_max=kwargs.get('stamps_max', 3),
            target_value=kwargs.get('target_value', 10),
            max_value=kwargs.get('max_value', 30),
            allow_stamp_repeat=kwargs.get('allow_stamp_repeat', False),
        )


class User(AbstractUser):
    stamps_min = models.IntegerField(default=1)
    stamps_max = models.IntegerField(default=3)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, default=75)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    allow_stamp_repeat = models.BooleanField(default=False)

    objects = UserCustomManager()

    @property
    def calc_settings(self):
        return {
            'stamps_min': self.stamps_min,
            'stamps_max': self.stamps_max,
            'target_value': self.target_value,
            'max_value': self.max_value,
        }

    @calc_settings.setter
    def calc_settings(self, settings: dict):
        self.stamps_min = settings['stamps_min']
        self.stamps_max = settings['stamps_max']
        self.target_value = settings['target_value']
        self.max_value = settings['max_value']

    @property
    def desk_available(self):
        from combinations.models import DeskType
        Desk = apps.get_model('combinations', 'Desk')
        return Desk.objects.get(user=self, type=DeskType.AVAILABLE)

    @property
    def desk_postcard(self):
        from combinations.models import DeskType
        Desk = apps.get_model('combinations', 'Desk')
        return Desk.objects.get(user=self, type=DeskType.POSTCARD)

    @property
    def desk_removed(self):
        from combinations.models import DeskType
        Desk = apps.get_model('combinations', 'Desk')
        return Desk.objects.get(user=self, type=DeskType.REMOVED)
