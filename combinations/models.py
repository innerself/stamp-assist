import datetime
import itertools
import math
import random
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
from django.utils.text import slugify
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from mimesis import Text, Locale, Datetime, Address, Finance, BinaryFile

from accounts.models import User
from stamp_assist.settings import env

imagekit = ImageKit(
    private_key=env('IMAGE_KIT_PRIVATE_KEY'),
    public_key=env('IMAGE_KIT_PUBLIC_KEY'),
    url_endpoint=env('IMAGE_KIT_ENDPOINT'),
)

logger = getLogger()

mim_text_en = Text(locale=Locale.EN)
mim_datetime = Datetime()
mim_address_en = Address(locale=Locale.EN)
mim_finance = Finance()
mim_binary_file = BinaryFile()


class DeskType(models.TextChoices):
    """
    AVAILABLE: stamps that user has
    POSTCARD: stamp that user put on the virtual postcard
    """
    AVAILABLE = 'available'
    POSTCARD = 'postcard'
    REMOVED = 'removed'


class DeskManager(models.QuerySet):
    pass


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

        # Remove duplicate combinations, where stamps have the same sample,
        # but because of different ids it becomes another combination
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


class StampSampleManager(models.QuerySet):
    def from_colnect_url(self, url: str):
        """Create an instance from colnect.com URL."""
        if self.filter(url=url).exists():
            logger.warning(f'Sample from URL: {url} already imported')
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/104.0.5112.79 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            image_url = f"https:{soup.find('div', {'class': 'item_z_pic'}).img['src']}"
        except AttributeError:
            logger.debug(f'Error importing image: {url}')
            return None

        ik_options = UploadFileRequestOptions(folder='/stamp-assist/')
        ik_image = imagekit.upload_file(
            image_url,
            file_name=Path(image_url).name,
            options=ik_options,
        )

        name = soup.find('span', id='name').string
        value = Decimal(soup.find(
            'dt', string='Номинальная стоимость:'
        ).next_sibling.next_element.text.replace(',', '.'))

        if michel_tag := soup.find('strong', string='Михель'):
            michel_number = michel_tag.next_sibling.text.strip()
        else:
            michel_number = None

        return self.create(
            name=name,
            slug=slugify(f'{name}-{value}'),
            year=datetime.date.fromisoformat(soup.find('dt', string='Дата выпуска:').next_sibling.text.strip()).year,
            country=soup.find('dt', string='Страна:').next_sibling.text.strip(),
            value=value,
            michel_number=michel_number,
            image=ik_image.url,
            url=url,
        )

    def update_slugs(self):
        for card in self.all():
            card.slug = slugify(f'{card.name}-{card.value}')
            card.save()

    def generate(self, **kwargs):
        name = kwargs.get('name', mim_text_en.title())
        return self.create(
            name=name,
            slug=slugify(name),
            year=kwargs.get('year', mim_datetime.year()),
            country=kwargs.get('country', mim_address_en.country()),
            value=kwargs.get('value', mim_finance.price(1, 101)),
            width=kwargs.get('width', random.randint(50, 400)),
            height=kwargs.get('height', random.randint(50, 400)),
            topics=kwargs.get('topics', mim_text_en.words(3)),
            michel_number=kwargs.get('michel_number', f'{mim_address_en.country_code()} {random.randint(1000, 9999)}'),
            image=kwargs.get('image', mim_binary_file.image()),
        )


class StampSample(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    year = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.PositiveSmallIntegerField(null=True)
    height = models.PositiveSmallIntegerField(null=True)
    topics = models.JSONField(default=list)
    michel_number = models.CharField(max_length=255, null=True, blank=True)
    image = models.URLField(null=True)
    url = models.URLField(null=True, max_length=500)

    objects = StampSampleManager().as_manager()

    def __str__(self):
        return f'{self.name} ({self.value}, {self.year})'


class UserStampManager(models.QuerySet):
    def generate(self, *, user: User, **kwargs):
        desk = Desk.objects.get(user=user, type=DeskType.AVAILABLE)
        return self.create(
            sample=kwargs.get('sample', StampSample.objects.generate()),
            custom_name=kwargs.get('custom_name'),
            comment=kwargs.get('comment'),
            user=user,
            desk=kwargs.get('desk', desk),
            allow_repeat=kwargs.get('allow_repeat', False),
        )

    def to_json(self) -> list[dict]:
        return [{
            'sample_slug': stamp.sample.slug,
            'custom_name': stamp.custom_name,
            'comment': stamp.comment,
            'username': stamp.user.username,
            'desk_type': stamp.desk.type,
            'allow_repeat': stamp.allow_repeat,
        } for stamp in self]

    def from_json(self, stamps_raw_data: list[dict]) -> list:
        created_stamps = []
        for stamp in stamps_raw_data:
            user = User.objects.get(username=stamp['username'])
            created_stamp = self.create(
                sample=StampSample.objects.get(slug=stamp['sample_slug']),
                custom_name=stamp['custom_name'],
                comment=stamp['comment'],
                user=user,
                desk=Desk.objects.get(user=user, type=stamp['desk_type']),
                allow_repeat=stamp['allow_repeat'],
            )
            created_stamps.append(created_stamp)

        return created_stamps


class UserStamp(models.Model):
    sample = models.ForeignKey(StampSample, on_delete=models.CASCADE)
    custom_name = models.CharField(max_length=255, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='stamps', on_delete=models.CASCADE)
    desk = models.ForeignKey(Desk, related_name='stamps', on_delete=models.PROTECT, null=True)
    allow_repeat = models.BooleanField(default=False)

    objects = UserStampManager.as_manager()

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
