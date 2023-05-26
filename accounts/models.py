from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    stamps_count = models.IntegerField(default=2)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, default=75)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, default=100)

    @property
    def calc_settings(self):
        return {
            'stamps_count': self.stamps_count,
            'target_value': self.target_value,
            'max_value': self.max_value,
        }

    @calc_settings.setter
    def calc_settings(self, settings: dict):
        self.stamps_count = settings['stamps_count']
        self.target_value = settings['target_value']
        self.max_value = settings['max_value']
