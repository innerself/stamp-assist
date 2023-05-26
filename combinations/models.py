import itertools
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Desk(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class StampCollection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def all_stamps(self, exclude_values: list[int] = None):
        stamps = []
        for block in self.blocks.all():
            stamps.extend([block.stamp] * block.number)
        return stamps

    def combinations(self):
        comb_groups = []
        combs = []
        comb_strings = []
        if self.user.stamps_count == 0:
            for st_num in range(1, 6):
                comb_groups.append(set(itertools.combinations(self.all_stamps(), st_num)))
        else:
            comb_groups.append(itertools.combinations(self.all_stamps(), self.user.stamps_count))

        for comb_group in comb_groups:
            for comb in comb_group:
                value_applies = self.user.target_value <= (c_sum := sum(comb)) <= self.user.max_value
                if value_applies and (c_srt := sorted(comb)) not in combs:
                    combs.append(c_srt)
                    comb_str = "<br> + ".join([str(x) for x in comb])
                    comb_strings.append(f'{comb_str}<br> = {c_sum}')

        return comb_strings

    def __str__(self):
        return f'{self.user} stamps collection'


class Stamp(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    topic = models.CharField(max_length=255, null=True, blank=True)
    desk = models.ForeignKey(Desk, on_delete=models.PROTECT, null=True)

    def __add__(self, other) -> Decimal:
        if isinstance(other, self.__class__):
            return self.value + other.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.value + other

    def __radd__(self, other):
        return self + other

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.value < other.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.value < other

    def __str__(self):
        if self.name:
            return f'{self.name} ({self.value})'
        else:
            return f'Stamp id={self.id} value={self.value}'


class StampBlock(models.Model):
    stamp = models.ForeignKey(Stamp, on_delete=models.CASCADE)
    number = models.IntegerField(default=1)
    collection = models.ForeignKey(StampCollection, related_name='blocks', on_delete=models.CASCADE)

    def __str__(self):
        return f'Stamp block {self.stamp} ({self.number} stamps)'


@receiver(post_save, sender=User)
def desk_create(sender, instance=None, created=False, **kwargs):
    if created:
        Desk.objects.create(user=instance)

