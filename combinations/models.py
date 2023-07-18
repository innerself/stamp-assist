import datetime
import itertools
import math
import time
from dataclasses import dataclass
from decimal import Decimal
from logging import getLogger
from pathlib import Path
from typing import Self

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from accounts.models import User
from stamp_assist.settings import env

imagekit = ImageKit(
    private_key=env('IMAGE_KIT_PRIVATE_KEY'),
    public_key=env('IMAGE_KIT_PUBLIC_KEY'),
    url_endpoint=env('IMAGE_KIT_ENDPOINT'),
)

logger = getLogger()


class DeskType(models.TextChoices):
    """
    AVAILABLE: stamps that user has
    POSTCARD: stamp that user put on the virtual postcard
    """
    AVAILABLE = 'available'
    POSTCARD = 'postcard'
    REMOVED = 'removed'


class Desk(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='desks', on_delete=models.CASCADE)
    type = models.CharField(max_length=100, choices=DeskType.choices)

    def __repr__(self):
        return f'{self.type.capitalize()} ({self.user.username})'

    @classmethod
    def desk_available(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.AVAILABLE)

    @classmethod
    def desk_postcard(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.POSTCARD)

    @classmethod
    def desk_removed(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.REMOVED)

    def combinations(self):
        if self.user.allow_stamp_repeat:
            all_stamps = UserStamp.objects \
                .filter(user=self.user) \
                .exclude(desk=self.desk_removed(self.user))
        else:
            all_stamps = []
            added_samples = []
            for stamp in UserStamp.objects \
                    .filter(user=self.user) \
                    .exclude(desk=self.desk_removed(self.user)):

                if stamp.allow_repeat:
                    all_stamps.append(stamp)
                elif stamp.sample not in added_samples:
                    all_stamps.append(stamp)
                    added_samples.append(stamp.sample)

        combs_to_test = []
        result_combs = []
        total_combs = 0

        start = time.perf_counter()
        if self.user.stamps_count == 0:
            for st_num in range(1, 6):
                total_combs += math.comb(len(all_stamps), st_num)
                combs_to_test.append(itertools.combinations(all_stamps, st_num))
        else:
            total_combs += math.comb(len(all_stamps), self.user.stamps_count)
            combs_to_test.append(itertools.combinations(all_stamps, self.user.stamps_count))

        print(f'User {self.user.username} requested to evaluate {total_combs} combinations')

        flt = set()
        flt_check = set()
        for index, c in enumerate(itertools.chain(*combs_to_test)):
            print(f'{index}/{total_combs}', end='\r')
            if (t := tuple(sorted(x.sample.name for x in c))) not in flt_check:
                flt_check.add(t)
                flt.add(tuple(sorted([(x.sample.name, x.id) for x in c])))

        print(f't1: {time.perf_counter() - start}')

        stamp_ids_on_pc = UserStamp.objects \
            .filter(user=self.user, desk=Desk.desk_postcard(self.user)) \
            .values_list('id', flat=True)
        for index, comb_to_test in enumerate(flt):
            comb_ids = [x[1] for x in comb_to_test]

            if stamp_ids_on_pc and not set(stamp_ids_on_pc).issubset(comb_ids):
                continue

            comb_db_objs = [x for x in all_stamps if x.id in comb_ids]
            value_applies = self.user.target_value <= sum(comb_db_objs) <= self.user.max_value
            if value_applies:
                result_combs.append(Combination(comb_db_objs))

        return sorted(result_combs, key=lambda x: x.sum())


class StampSampleManager(models.Manager):
    def from_colnect(self, url: str):
        """Create an instance from colnect.com URL."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/104.0.5112.79 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        image_url = f"https:{soup.find('div', {'class': 'item_z_pic'}).img['src']}"
        ik_options = UploadFileRequestOptions(folder='/stamp-assist/')
        ik_image = imagekit.upload_file(
            image_url,
            file_name=Path(image_url).name,
            options=ik_options,
        )

        return self.create(
            name=soup.find('span', id='name').string,
            year=datetime.date.fromisoformat(soup.find('dt', string='Дата выпуска:').next_sibling.text.strip()).year,
            country=soup.find('dt', string='Страна:').next_sibling.text.strip(),
            value=int(soup.find('dt', string='Номинальная стоимость:').next_sibling.next_element.text),
            michel_number=soup.find('strong', string='Михель').next_sibling.text.strip(),
            image=ik_image.url,
        )


class StampSample(models.Model):
    name = models.CharField(max_length=255)
    year = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.PositiveSmallIntegerField(null=True)
    height = models.PositiveSmallIntegerField(null=True)
    topics = models.JSONField(default=list)
    michel_number = models.CharField(max_length=255, null=True, blank=True)
    image = models.URLField(null=True)

    objects = StampSampleManager()

    def __str__(self):
        return f'{self.name} ({self.value}, {self.year})'


class UserStamp(models.Model):
    sample = models.ForeignKey(StampSample, on_delete=models.CASCADE)
    custom_name = models.CharField(max_length=255, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='stamps', on_delete=models.CASCADE)
    desk = models.ForeignKey(Desk, related_name='stamps', on_delete=models.PROTECT, null=True)
    allow_repeat = models.BooleanField(default=False)

    def __add__(self, other) -> Decimal:
        if isinstance(other, self.__class__):
            return self.sample.value + other.sample.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.sample.value + other

    def __radd__(self, other) -> Decimal:
        return self + other

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.sample.value < other.sample.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.sample.value < other

    def __str__(self):
        if self.sample.name:
            return f'{self.sample.name} ({self.sample.value})'
        else:
            return f'id={self.id} value={self.sample.value}'


@receiver(post_save, sender=User)
def desk_create(sender, instance=None, created=False, **kwargs):
    if created:
        Desk.objects.create(user=instance, type=DeskType.AVAILABLE)
        Desk.objects.create(user=instance, type=DeskType.POSTCARD)
        Desk.objects.create(user=instance, type=DeskType.REMOVED)


@dataclass
class Combination:
    stamps: list[UserStamp]

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            self_names = sorted([x.sample.name for x in self.stamps])
            other_names = sorted([x.sample.name for x in other.stamps])
            return self_names == other_names

        return NotImplemented

    def sum(self) -> Decimal:
        return sum(self.stamps)
